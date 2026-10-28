"""Opt-in shared spatial residual over the legacy coordinate action logits.

Uses only current observation tensors. No routes, candidate endpoints or
demonstrations are supplied. Zero residual initialization preserves the old
policy when its global encoder/actor/critic weights are copied explicitly.
"""
import torch
from torch import nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor,MlpExtractor
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy


class SpatialResidualFeatures(BaseFeaturesExtractor):
    def __init__(self,observation_space):
        from train import GridEncoder
        super().__init__(observation_space,features_dim=1628)
        self.global_encoder=GridEncoder(observation_space)
        channels=observation_space['grid'].shape[0]
        self.spatial=nn.Sequential(nn.Conv2d(channels+7,16,1),nn.ReLU(),
            nn.Conv2d(16,16,3,padding=2,dilation=2,groups=16),nn.ReLU(),nn.Conv2d(16,16,1),nn.ReLU(),
            nn.Conv2d(16,16,3,padding=4,dilation=4,groups=16),nn.ReLU(),nn.Conv2d(16,16,1),nn.ReLU())
        self.global_context=nn.Sequential(nn.Linear(42,8),nn.Tanh())
        self.spatial_head=nn.Sequential(nn.Conv2d(24,16,1),nn.ReLU(),nn.Conv2d(16,1,1))
        nn.init.zeros_(self.spatial_head[-1].weight);nn.init.zeros_(self.spatial_head[-1].bias)
        y,x=torch.meshgrid(torch.arange(30)/30,torch.arange(50)/50,indexing='ij')
        self.register_buffer('x',x.reshape(1,1,30,50),persistent=False)
        self.register_buffer('y',y.reshape(1,1,30,50),persistent=False)

    def forward(self,obs):
        grid=obs['grid'];n=grid.shape[0];marker=grid[:,48:49]
        selected=marker.sum((2,3),keepdim=True)
        dx=(self.x-(marker*self.x).sum((2,3),keepdim=True))*selected
        dy=(self.y-(marker*self.y).sum((2,3),keepdim=True))*selected
        kind=grid[:,10:12]
        valid=kind.sum(1,keepdim=True)
        color=(grid[:,12:20]*marker*valid).sum((2,3),keepdim=True)
        match=(grid[:,12:20]*color).sum(1,keepdim=True)*valid
        selected_kind=(kind*marker).sum((2,3),keepdim=True).expand(-1,-1,30,50)
        inputs=torch.cat([grid,self.x.expand(n,-1,-1,-1),self.y.expand(n,-1,-1,-1),dx,dy,match,selected_kind],dim=1)
        local=self.spatial(inputs)
        context=self.global_context(obs['global']).unsqueeze(-1).unsqueeze(-1).expand(-1,-1,30,50)
        residual=self.spatial_head(torch.cat([local,context],dim=1)).flatten(1)
        return torch.cat([self.global_encoder(obs),residual],dim=1)


class ResidualMlp(nn.Module):
    def __init__(self,device):
        super().__init__();self.global_mlp=MlpExtractor(128,net_arch=[64],activation_fn=nn.Tanh,device=device)
        self.latent_dim_pi=1564;self.latent_dim_vf=64

    def forward(self,features):return self.forward_actor(features),self.forward_critic(features)
    def forward_actor(self,features):return torch.cat([self.global_mlp.forward_actor(features[:,:128]),features[:,128:]],dim=1)
    def forward_critic(self,features):return self.global_mlp.forward_critic(features[:,:128])


class ResidualActions(nn.Module):
    def __init__(self):super().__init__();self.base=nn.Linear(64,1513)
    def forward(self,latent):
        logits=self.base(latent[:,:64])
        return torch.cat([logits[:,:1500]+latent[:,64:],logits[:,1500:]],dim=1)


class SpatialResidualPolicy(MaskableActorCriticPolicy):
    def __init__(self,*args,**kwargs):
        kwargs['features_extractor_class']=SpatialResidualFeatures;kwargs['normalize_images']=False
        super().__init__(*args,**kwargs)

    def _build(self,lr_schedule):
        self.mlp_extractor=ResidualMlp(self.device)
        self.action_net=ResidualActions();self.value_net=nn.Linear(64,1)
        self.optimizer=self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)
