"""Train growing-city decisions while preserving the verified opening policy."""

import torch
from torch import nn

from city_road_policy import ROAD_SLOTS
from city_route_repair_policy import RouteProgressPolicy, RouteRepairFeatures


class CityGrowthFeatures(RouteRepairFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space, frontier=True, progress=True, calibrated=True)
        channels = observation_space['grid'].shape[0]
        self.growth_grid = nn.Sequential(
            nn.Conv2d(channels, 16, 1), nn.SiLU(),
            nn.Conv2d(16, 16, 3, padding=1), nn.SiLU(),
        )
        self.growth_context = nn.Linear(self.context_width, 16)
        self.growth_roads = nn.Conv2d(16, 4, 1)
        self.growth_wait = nn.Sequential(nn.Linear(self.context_width, 32), nn.SiLU(), nn.Linear(32, 1))
        for layer in (self.growth_roads, self.growth_wait[-1]):
            nn.init.zeros_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, observations):
        # Optional cache scoped by the enclosing wide-policy forward call.
        # Only reuse frozen computations; never cache a live autograd graph.
        cache = getattr(self, '_growth_features_cache', None)
        cacheable = cache is not None and not torch.is_grad_enabled()
        key = id(observations)
        if cacheable and key in cache:
            return cache[key][1]
        with torch.no_grad():
            base = super().forward(observations)
        wait_index = ROAD_SLOTS + self.context_width
        pooled = base[:, ROAD_SLOTS:wait_index]
        # The last feature is a positive coupling for states handled by the repaired opening policy.
        growing = (base[:, -1:] == 0).to(base.dtype)
        features = self.growth_grid(observations['grid'])
        features = torch.nn.functional.silu(features + self.growth_context(pooled)[:, :, None, None])
        roads = self.growth_roads(features).permute(0, 2, 3, 1).reshape(-1, ROAD_SLOTS)
        wait = self.growth_wait(pooled)
        result = torch.cat((
            base[:, :ROAD_SLOTS] + growing * roads,
            pooled,
            base[:, wait_index:wait_index+1] + growing * wait,
            base[:, wait_index+1:],
        ), dim=1)
        if cacheable:
            cache[key] = (observations, result)
        return result


class CityGrowthPolicy(RouteProgressPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.features_extractor.named_parameters():
            parameter.requires_grad_(name.startswith('growth_'))
        self.optimizer = self.optimizer_class(
            filter(lambda parameter: parameter.requires_grad, self.parameters()),
            lr=lr_schedule(1), **self.optimizer_kwargs,
        )
