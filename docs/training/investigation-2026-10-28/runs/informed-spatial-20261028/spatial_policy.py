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
    def __init__(self,cell_scale=1.):super().__init__();self.base=nn.Linear(64,1513);self.cell_scale=cell_scale
    def forward(self,latent):
        logits=self.base(latent[:,:64])
        return torch.cat([self.cell_scale*logits[:,:1500]+latent[:,64:],logits[:,1500:]],dim=1)


class SpatialResidualPolicy(MaskableActorCriticPolicy):
    feature_class=SpatialResidualFeatures
    mlp_class=ResidualMlp
    action_class=ResidualActions
    def __init__(self,*args,**kwargs):
        kwargs['features_extractor_class']=self.feature_class;kwargs['normalize_images']=False
        super().__init__(*args,**kwargs)

    def _build(self,lr_schedule):
        self.mlp_extractor=self.mlp_class(self.device)
        self.action_net=self.action_class(getattr(self,'cell_scale',1.));self.value_net=nn.Linear(64,1)
        self.optimizer=self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)


class InformedSpatialFeatures(SpatialResidualFeatures):
    def __init__(self,observation_space):
        if observation_space['grid'].shape[0]!=52:raise ValueError('Informed spatial policy requires connectivity inputs')
        super().__init__(observation_space)
        self._features_dim=1641
        self.prior_strength=nn.Parameter(torch.tensor(6.))

    @staticmethod
    def shift(values,dx,dy):
        shifted=torch.roll(values,(dy,dx),(2,3)).clone()
        if dx>0:shifted[:,:,:,:dx]=0
        if dx<0:shifted[:,:,:,dx:]=0
        if dy>0:shifted[:,:,:dy]=0
        if dy<0:shifted[:,:,dy:]=0
        return shifted

    def forward(self,obs):
        features=super().forward(obs);grid=obs['grid'];global_state=obs['global']
        colors=grid[:,12:20];house=grid[:,10:11];shop=grid[:,11:12]
        missing_house=grid[:,50:51];missing_shop=grid[:,51:52]
        needed_colors=(colors*shop*missing_shop).sum((2,3),keepdim=True).clamp(0,1)
        house_need=(missing_house+(colors*needed_colors).sum(1,keepdim=True)*house).clamp(0,1)
        sources=torch.zeros_like(colors);destinations=torch.zeros_like(colors);unsupplied=torch.zeros_like(colors)
        for d,(dx,dy) in enumerate([(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]):
            entrance=grid[:,32+d:33+d]
            sources+=self.shift(colors*house*house_need*entrance,dx,dy)
            destinations+=self.shift(colors*shop*entrance,dx,dy)
            unsupplied+=self.shift(colors*shop*missing_shop*entrance,dx,dy)
        marker=grid[:,48:49]
        selected_color=(marker*(sources+colors*house)).sum((2,3),keepdim=True).clamp(0,1)
        has_color=selected_color.sum(1,keepdim=True).clamp(0,1)
        match=(destinations*selected_color).sum(1,keepdim=True)+(1-has_color)*destinations.sum(1,keepdim=True)
        first_x=(marker*self.x).sum((2,3),keepdim=True);first_y=(marker*self.y).sum((2,3),keepdim=True)
        distance=((self.x-first_x).abs()*50+(self.y-first_y).abs()*30)/10
        alpha=self.prior_strength.clamp(0,12)
        start_logits=alpha*sources.sum(1,keepdim=True).clamp(0,1)
        end_logits=(alpha+unsupplied.sum(1,keepdim=True).clamp(0,1)-distance.clamp(max=3))*match.clamp(0,1)
        draw=global_state[:,30,None,None,None]
        first=global_state[:,26,None,None,None];end=global_state[:,27,None,None,None]
        prior=(draw*(first*start_logits+end*end_logits)).flatten(1)
        no_goals=(sources.sum((1,2,3))==0).to(features.dtype)
        tool_prior=torch.zeros(grid.shape[0],13,device=grid.device,dtype=grid.dtype)
        tool_prior[:,0]=no_goals*8
        tool_prior[:,11]=10*(global_state[:,9:15].sum(1)>0).to(grid.dtype)
        tool_prior[:,12]=10*(global_state[:,17:23].sum(1)>0).to(grid.dtype)
        # Explicit domain priors, not routed suggestions or a learning result.
        return torch.cat([features[:,:128],features[:,128:]+prior,tool_prior],dim=1)


class InformedMlp(ResidualMlp):
    def __init__(self,device):super().__init__(device);self.latent_dim_pi=1577
    def forward_actor(self,features):return torch.cat([self.global_mlp.forward_actor(features[:,:128]),features[:,128:]],dim=1)


class InformedActions(ResidualActions):
    def forward(self,latent):
        base=self.base(latent[:,:64])
        return torch.cat([self.cell_scale*base[:,:1500],base[:,1500:]],dim=1)+latent[:,64:]


class InformedSpatialPolicy(SpatialResidualPolicy):
    feature_class=InformedSpatialFeatures
    mlp_class=InformedMlp
    action_class=InformedActions
    def __init__(self,*args,**kwargs):
        self.cell_scale=0.
        super().__init__(*args,**kwargs)
