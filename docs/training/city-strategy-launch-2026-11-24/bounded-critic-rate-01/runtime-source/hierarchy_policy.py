"""Shared visible encoder with separate manager/executor policy and value heads.

No learning entry point. Uses the published encoder widths; focus adds two input
planes, role/option context is fused explicitly. Weekly head comes with the
full-game action-context implementation; Stage 1 has no weekly offers.
"""
import math
import torch
from torch import nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy


class HierarchyFeatures(BaseFeaturesExtractor):
    def __init__(self, observation_space):
        # Last scalar selects the head, rather than entering the shared head MLP.
        super().__init__(observation_space, features_dim=257)
        channels = observation_space['grid'].shape[0]+2
        self.board = nn.Sequential(nn.Conv2d(channels,32,3,padding=1),nn.ReLU(),
            nn.Conv2d(32,64,3,stride=2,padding=1),nn.ReLU(),
            nn.Conv2d(64,64,3,stride=2,padding=1),nn.ReLU(),
            nn.AdaptiveAvgPool2d((4,7)),nn.Flatten(),nn.Linear(1792,256),nn.ReLU())
        self.global_encoder = nn.Sequential(nn.Linear(54,64),nn.ReLU())
        self.motorway_encoder = nn.Sequential(nn.Linear(6,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
        size = observation_space['context'].shape[0]
        self.fuse = nn.Sequential(nn.Linear(384+size,256),nn.ReLU())

    def forward(self, obs):
        board = self.board(torch.cat((obs['grid'],obs['focus']),dim=1))
        rows = self.motorway_encoder(obs['motorways'])
        valid = obs['motorways'][...,5:6] > .5
        count = valid.sum(dim=1)
        mean = (rows*valid).sum(dim=1)/count.clamp(min=1)
        maximum = rows.masked_fill(~valid,-torch.inf).amax(dim=1)
        maximum = torch.where(count>0,maximum,torch.zeros_like(maximum))
        features = self.fuse(torch.cat((board,self.global_encoder(obs['global']),mean,maximum,obs['context']),dim=1))
        is_manager = obs['context'][:,0:2].sum(dim=1,keepdim=True)
        return torch.cat((features,is_manager),dim=1)


class RoleMLP(nn.Module):
    latent_dim_pi = latent_dim_vf = 257
    def forward(self,x): return x,x
    def forward_actor(self,x): return x
    def forward_critic(self,x): return x


class RoleHead(nn.Module):
    def __init__(self, output, gain):
        super().__init__()
        self.manager = nn.Sequential(nn.Linear(256,128),nn.Tanh(),nn.Linear(128,output))
        self.executor = nn.Sequential(nn.Linear(256,128),nn.Tanh(),nn.Linear(128,output))
        for head in (self.manager,self.executor):
            nn.init.orthogonal_(head[0].weight,math.sqrt(2));nn.init.zeros_(head[0].bias)
            nn.init.orthogonal_(head[2].weight,gain);nn.init.zeros_(head[2].bias)

    def forward(self, features):
        manager,executor = self.manager(features[:,:256]),self.executor(features[:,:256])
        return torch.where(features[:,256:257]>.5,manager,executor)


class HierarchyPolicy(MaskableActorCriticPolicy):
    def __init__(self,*args,**kwargs):
        kwargs.update(features_extractor_class=HierarchyFeatures,normalize_images=False)
        kwargs.setdefault('optimizer_kwargs', {'eps':1e-5})
        super().__init__(*args,**kwargs)

    def _build_mlp_extractor(self):
        self.mlp_extractor = RoleMLP()

    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        self.action_net = RoleHead(self.action_space.n,.01)
        self.value_net = RoleHead(1,1)
        self.optimizer = self.optimizer_class(self.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)


def practice_policy(env, lr_schedule):
    if env.direct:
        return MaskableActorCriticPolicy(
            env.observation_space, env.action_space, lr_schedule,
            features_extractor_class=HierarchyFeatures, normalize_images=False,
            net_arch=dict(pi=[128], vf=[128]), optimizer_kwargs={'eps': 1e-5},
        )
    return HierarchyPolicy(env.observation_space, env.action_space, lr_schedule)
