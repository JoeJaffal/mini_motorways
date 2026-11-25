"""Learn opening corrections while keeping established-city behavior fixed."""
from copy import deepcopy

import torch
from torch import nn

from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from city_strategy_policy import STRATEGY_CONTEXT
from city_wide_strategy_policy import CityWideStrategyFeatures, CityWideStrategyPolicy, SPATIAL_CONTEXT


class CityOpeningStrategyFeatures(CityWideStrategyFeatures):
    def __init__(self, observation_space, **kwargs):
        super().__init__(observation_space, **kwargs)
        self.opening_strategy_spatial = deepcopy(self.growth_strategy_spatial)
        self.opening_strategy_roads = nn.Conv2d(16, 4, 1)
        self.opening_strategy_wait = nn.Sequential(
            nn.Linear(STRATEGY_CONTEXT + SPATIAL_CONTEXT, 32), nn.SiLU(), nn.Linear(32, 1))
        for layer in (self.opening_strategy_roads, self.opening_strategy_wait[-1]):
            nn.init.zeros_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, observations):
        with torch.no_grad():
            base = super().forward(observations)
            context, established = self.strategy_context(observations)
        spatial = self.opening_strategy_spatial(observations['grid'])
        visible = observations['grid'][:, :1] > 0
        count = visible.sum((2, 3))
        mean = (spatial * visible).sum((2, 3)) / count.clamp_min(1)
        maximum = spatial.masked_fill(~visible, torch.finfo(spatial.dtype).min).amax((2, 3))
        maximum = torch.where(count > 0, maximum, torch.zeros_like(maximum))
        active = (~established.bool()).to(base.dtype)
        roads = self.opening_strategy_roads(spatial).permute(0, 2, 3, 1).reshape(-1, ROAD_SLOTS)
        wait = self.opening_strategy_wait(torch.cat((context, mean, maximum), dim=1))
        index = ROAD_SLOTS + self.context_width
        return torch.cat((base[:, :ROAD_SLOTS] + roads * active, base[:, ROAD_SLOTS:index],
                          base[:, index:index+1] + wait * active, base[:, index+1:]), dim=1)


class CityOpeningStrategyPolicy(CityWideStrategyPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        f = self.features_extractor
        for name, parameter in f.named_parameters():
            parameter.requires_grad_(name.startswith('opening_strategy_'))
        self.optimizer = RelativeRateAdam([
            dict(params=list(f.opening_strategy_wait.parameters()), lr_scale=1.),
            dict(params=list(f.opening_strategy_roads.parameters()), lr_scale=.3),
            dict(params=list(f.opening_strategy_spatial.parameters()), lr_scale=.1),
            dict(params=list(self.value_net.parameters()), lr_scale=.1),
        ], lr=lr_schedule(1), **self.optimizer_kwargs)
