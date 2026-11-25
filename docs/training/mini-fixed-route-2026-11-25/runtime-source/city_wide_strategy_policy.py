"""Learn whole-board spatial corrections without generating routes or targets."""
import torch
from torch import nn
from city_strategy_policy import CityStrategyFeatures,CityStrategyPolicy,StrategyHead,StrategyLatents,STRATEGY_CONTEXT
from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS

SPATIAL_CONTEXT=32

class CityWideStrategyFeatures(CityStrategyFeatures):
    def __init__(self,observation_space,**kwargs):
        super().__init__(observation_space,**kwargs)
        channels=observation_space['grid'].shape[0]
        layers=[nn.Conv2d(channels,16,1),nn.SiLU()]
        # A 63-cell receptive field greatly expands the trainable spatial view.
        # These are learned convolutions, not path search or a road builder.
        for dilation in (1,2,4,8,16):
            layers.extend((nn.Conv2d(16,16,3,padding=dilation,dilation=dilation),nn.SiLU()))
        self.growth_strategy_spatial=nn.Sequential(*layers)
        self.growth_strategy_spatial_roads=nn.Conv2d(16,4,1)
        self.growth_strategy_visual_wait=nn.Sequential(nn.Linear(SPATIAL_CONTEXT,16),nn.SiLU(),nn.Linear(16,1))
        for layer in (self.growth_strategy_spatial_roads,self.growth_strategy_visual_wait[-1]):
            nn.init.zeros_(layer.weight);nn.init.zeros_(layer.bias)
        self._features_dim+=SPATIAL_CONTEXT

    def _evidence(self, name, raw_grid, compute):
        cache=getattr(self, '_evidence_cache', None)
        if cache is None or raw_grid.requires_grad:
            return compute(raw_grid)
        key=(name,id(raw_grid))
        if key not in cache:
            # Keep the input alive so its object id cannot be reused in this call.
            cache[key]=(raw_grid,compute(raw_grid))
        return cache[key][1]

    def service_features(self, raw_grid):
        return self._evidence('service',raw_grid,super().service_features)

    def relation_evidence(self, raw_grid):
        return self._evidence('relations',raw_grid,super().relation_evidence)

    def forward(self,observations):
        # Pure visible-state calculations repeat through the inherited actor
        # branches. Cache only inside this call; never across decisions/updates.
        previous=getattr(self,'_evidence_cache',None)
        self._evidence_cache={} if getattr(self,'evidence_cache_enabled',True) else None
        reference=getattr(self,'opening_reference',None)
        use_growth_cache=getattr(self,'growth_cache_enabled',False) and reference is not None
        previous_growth=getattr(reference,'_growth_features_cache',None)
        if use_growth_cache:reference._growth_features_cache={}
        try:
            return self._forward_uncached(observations)
        finally:
            self._evidence_cache=previous
            if use_growth_cache:reference._growth_features_cache=previous_growth

    def _forward_uncached(self,observations):
        base=super().forward(observations)
        context=base[:,-STRATEGY_CONTEXT:]
        established=self.strategy_gate(context[:,57:58])
        spatial=self.growth_strategy_spatial(observations['grid'])
        visible=observations['grid'][:,:1]>0
        count=visible.sum((2,3))
        mean=(spatial*visible).sum((2,3))/count.clamp_min(1)
        maximum=spatial.masked_fill(~visible,torch.finfo(spatial.dtype).min).amax((2,3))
        maximum=torch.where(count>0,maximum,torch.zeros_like(maximum))
        pooled=torch.cat((mean,maximum),dim=1)
        roads=self.growth_strategy_spatial_roads(spatial).permute(0,2,3,1).reshape(-1,ROAD_SLOTS)*established
        wait=self.growth_strategy_visual_wait(pooled)*established
        index=ROAD_SLOTS+self.context_width
        return torch.cat((base[:,:ROAD_SLOTS]+roads,base[:,ROAD_SLOTS:index],base[:,index:index+1]+wait,base[:,index+1:],pooled),dim=1)

class WideStrategyHead(StrategyHead):
    def forward(self,features):return super().forward(features[:,:-SPATIAL_CONTEXT])

class WideStrategyLatents(StrategyLatents):
    def forward_critic(self,features):
        return torch.cat((super().forward_critic(features[:,:-SPATIAL_CONTEXT]),features[:,-SPATIAL_CONTEXT:]),dim=1)

class CityWideStrategyPolicy(CityStrategyPolicy):
    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        self.action_net=WideStrategyHead(self.features_extractor.context_width)
        self.action_net.requires_grad_(False)
        self.mlp_extractor=WideStrategyLatents()
        self.value_net=nn.Sequential(nn.Linear(self.value_net[0].in_features+SPATIAL_CONTEXT,64),nn.SiLU(),nn.Linear(64,1))
        f=self.features_extractor
        self.optimizer=RelativeRateAdam([
            dict(params=[*f.growth_strategy_wait.parameters(),*f.growth_strategy_visual_wait.parameters()],lr_scale=1.),
            dict(params=[*f.growth_strategy_roads.parameters(),*f.growth_strategy_spatial_roads.parameters()],lr_scale=.3),
            dict(params=list(f.growth_strategy_spatial.parameters()),lr_scale=.1),
            dict(params=list(self.value_net.parameters()),lr_scale=.1),
        ],lr=lr_schedule(1),**self.optimizer_kwargs)
