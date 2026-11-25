"""Native-score PPO residuals over visible city evidence; no teacher actions."""
import torch
from torch import nn
from city_relational_policy import CitySharpRelationsFeatures,RelativeRateAdam
from city_growth_policy import CityGrowthPolicy
from city_route_repair_policy import ProgressHead,ProgressLatents
from city_road_policy import ROAD_SLOTS
from midgame_timing_policy import MidgameTimingFeatures

STRATEGY_CONTEXT=64

class CityStrategyFeatures(CitySharpRelationsFeatures):
    def __init__(self, observation_space, **kwargs):
        super().__init__(observation_space, **kwargs)
        if observation_space['global'].shape!=(54,):
            raise ValueError('Unexpected visible global schema')
        self._features_dim+=STRATEGY_CONTEXT
        self.growth_strategy_wait=nn.Sequential(nn.Linear(STRATEGY_CONTEXT,32),nn.SiLU(),nn.Linear(32,1))
        self.growth_strategy_roads=nn.Sequential(nn.Linear(STRATEGY_CONTEXT+10,32),nn.SiLU(),nn.Linear(32,1))
        for module in (self.growth_strategy_wait,self.growth_strategy_roads):
            nn.init.zeros_(module[-1].weight);nn.init.zeros_(module[-1].bias)

    def strategy_context(self, observations):
        grid=observations['grid'].flatten(2)
        _,_,_,available,established,quiet=self.service_features(observations['grid'])
        blocked=MidgameTimingFeatures.waiting_context(self,observations['grid'])
        houses=grid[:,19]*grid[:,29];shops=grid[:,20]*grid[:,29]
        demand=grid[:,41]*shops
        cars=(grid[:,57]/(1-grid[:,57]).clamp_min(.05)).clamp(max=20)
        summary=torch.cat((available.float(),quiet.float(),blocked.float(),established.float(),
            houses.sum(1,keepdim=True)/20,shops.sum(1,keepdim=True)/10,
            grid[:,9:17].bool().any(1).sum(1,keepdim=True)/200,
            demand.sum(1,keepdim=True)/10,demand.amax(1,keepdim=True),
            (cars*grid[:,62]).sum(1,keepdim=True)/40),dim=1)
        return torch.cat((observations['global'],summary.clamp(0,4)),dim=1),established

    def strategy_gate(self, established):
        return established

    def forward(self, observations):
        with torch.no_grad():
            base=super().forward(observations)
            context,established=self.strategy_context(observations)
            relations=self.relation_evidence(observations['grid'])
        evidence=torch.cat((relations,context[:,None].expand(-1,ROAD_SLOTS,-1)),dim=-1)
        roads=self.growth_strategy_roads(evidence).squeeze(-1)*self.strategy_gate(established)
        wait=self.growth_strategy_wait(context)*self.strategy_gate(established)
        index=ROAD_SLOTS+self.context_width
        return torch.cat((base[:,:ROAD_SLOTS]+roads,base[:,ROAD_SLOTS:index],
            base[:,index:index+1]+wait,base[:,index+1:],context),dim=1)

class StrategyHead(ProgressHead):
    def forward(self, features):
        return super().forward(features[:,:-STRATEGY_CONTEXT])

class StrategyLatents(ProgressLatents):
    def forward_critic(self, features):
        return torch.cat((super().forward_critic(features[:,:-STRATEGY_CONTEXT]),features[:,-STRATEGY_CONTEXT:]),dim=1)

class CityStrategyPolicy(CityGrowthPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.action_net=StrategyHead(self.features_extractor.context_width)
        self.action_net.requires_grad_(False)
        self.mlp_extractor=StrategyLatents()
        width=self.value_net[0].in_features+STRATEGY_CONTEXT
        self.value_net=nn.Sequential(nn.Linear(width,64),nn.SiLU(),nn.Linear(64,1))
        for name,p in self.features_extractor.named_parameters():
            p.requires_grad_(name.startswith('growth_strategy_'))
        self.optimizer=RelativeRateAdam([
            dict(params=list(self.features_extractor.growth_strategy_wait.parameters()),lr_scale=1.),
            dict(params=list(self.features_extractor.growth_strategy_roads.parameters()),lr_scale=.3),
            dict(params=list(self.value_net.parameters()),lr_scale=.1),
        ],lr=lr_schedule(1),**self.optimizer_kwargs)
