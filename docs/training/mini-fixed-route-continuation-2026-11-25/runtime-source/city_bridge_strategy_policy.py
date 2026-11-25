"""One masked connection policy with a learnable bridge choice and bridge scores.

Separately normalizing legal dry and water connections prevents an untrained
water-logit offset from making a newly exposed tool effectively unselectable.
This selects no route and receives no target actions. PPO sees the actual joint
categorical log probability, including the learned dry/water mixing weight.
"""
from copy import deepcopy
import math

import torch
from torch import nn
from torch.nn import functional as F

from city_relational_policy import RelativeRateAdam
from city_road_policy import ROAD_SLOTS
from city_route_repair_policy import ProgressDistribution
from city_strategy_policy import STRATEGY_CONTEXT
from city_wide_strategy_policy import (
    CityWideStrategyFeatures, CityWideStrategyPolicy, WideStrategyHead,
    WideStrategyLatents, SPATIAL_CONTEXT,
)

BRIDGE_METADATA = ROAD_SLOTS + 1


class CityBridgeStrategyFeatures(CityWideStrategyFeatures):
    def __init__(self, observation_space, **kwargs):
        super().__init__(observation_space, **kwargs)
        self.bridge_strategy_spatial = deepcopy(self.growth_strategy_spatial)
        self.bridge_strategy_roads = nn.Conv2d(16, 4, 1)
        self.bridge_strategy_choice = nn.Sequential(
            nn.Linear(STRATEGY_CONTEXT + SPATIAL_CONTEXT, 32), nn.SiLU(), nn.Linear(32, 1))
        nn.init.zeros_(self.bridge_strategy_roads.weight)
        nn.init.zeros_(self.bridge_strategy_roads.bias)
        nn.init.zeros_(self.bridge_strategy_choice[-1].weight)
        # Explicit exploration initialization, conditional on choosing Build
        # and both dry and water categories having native-legal connections.
        nn.init.constant_(self.bridge_strategy_choice[-1].bias, math.log(.2/.8))
        self._features_dim += BRIDGE_METADATA

    def forward(self, observations):
        with torch.no_grad():
            base = super().forward(observations)
            context, _ = self.strategy_context(observations)
            water = observations['grid'][:, 2].flatten(1) > 0
            water_edges = (water[:, self.starts] | water[:, self.ends]).to(base.dtype)
        spatial = self.bridge_strategy_spatial(observations['grid'])
        visible = observations['grid'][:, :1] > 0
        count = visible.sum((2, 3))
        mean = (spatial * visible).sum((2, 3)) / count.clamp_min(1)
        maximum = spatial.masked_fill(~visible, torch.finfo(spatial.dtype).min).amax((2, 3))
        maximum = torch.where(count > 0, maximum, torch.zeros_like(maximum))
        choice = self.bridge_strategy_choice(torch.cat((context, mean, maximum), dim=1))
        roads = self.bridge_strategy_roads(spatial).permute(0, 2, 3, 1).reshape(-1, ROAD_SLOTS)
        return torch.cat((base[:, :ROAD_SLOTS] + roads * water_edges,
                          base[:, ROAD_SLOTS:], water_edges, choice), dim=1)


class BridgeStrategyHead(WideStrategyHead):
    def forward(self, features):
        return torch.cat((super().forward(features[:, :-BRIDGE_METADATA]),
                          features[:, -BRIDGE_METADATA:]), dim=1)


class BridgeStrategyLatents(WideStrategyLatents):
    def forward_critic(self, features):
        return super().forward_critic(features[:, :-BRIDGE_METADATA])


class BridgeStrategyDistribution(ProgressDistribution):
    def proba_distribution(self, action_logits):
        self.water_edges = action_logits[:, -BRIDGE_METADATA:-1].bool()
        self.bridge_logit = action_logits[:, -1:]
        return super().proba_distribution(action_logits[:, :-BRIDGE_METADATA])

    def apply_masking(self, masks):
        original = self.raw_logits
        roads = original[:, 1:]
        legal = (torch.ones_like(original, dtype=torch.bool) if masks is None else
                 torch.as_tensor(masks, device=roads.device, dtype=torch.bool).reshape_as(original))
        wet = legal[:, 1:] & self.water_edges
        dry = legal[:, 1:] & ~self.water_edges
        has_wet, has_dry = wet.any(1, keepdim=True), dry.any(1, keepdim=True)
        # The empty-category branch uses a finite dummy normalizer and is
        # discarded below, avoiding NaNs in gradients for forced choices.
        wet_sum = roads.masked_fill(~wet & has_wet, -torch.inf).logsumexp(1, keepdim=True)
        dry_sum = roads.masked_fill(~dry & has_dry, -torch.inf).logsumexp(1, keepdim=True)
        mixed = torch.where(self.water_edges,
                            roads-wet_sum-F.softplus(-self.bridge_logit),
                            roads-dry_sum-F.softplus(self.bridge_logit))
        adjusted = torch.where(has_wet & has_dry, mixed, roads)
        self.raw_logits = torch.cat((original[:, :1], adjusted), dim=1)
        try:
            super().apply_masking(masks)
        finally:
            self.raw_logits = original


class CityBridgeStrategyPolicy(CityWideStrategyPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.action_net = BridgeStrategyHead(self.features_extractor.context_width)
        self.action_net.requires_grad_(False)
        self.mlp_extractor = BridgeStrategyLatents()
        self.action_dist = BridgeStrategyDistribution(self.action_space.n)
        f = self.features_extractor
        for name, parameter in f.named_parameters():
            parameter.requires_grad_(name.startswith('bridge_strategy_'))
        self.optimizer = RelativeRateAdam([
            dict(params=list(f.bridge_strategy_choice.parameters()), lr_scale=1.),
            dict(params=list(f.bridge_strategy_roads.parameters()), lr_scale=.3),
            dict(params=list(f.bridge_strategy_spatial.parameters()), lr_scale=.1),
            dict(params=list(self.value_net.parameters()), lr_scale=.1),
        ], lr=lr_schedule(1), **self.optimizer_kwargs)
