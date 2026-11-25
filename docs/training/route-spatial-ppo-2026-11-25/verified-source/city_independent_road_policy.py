"""An opt-in trainable road encoder with a preserved Wait representation."""
from copy import deepcopy
import torch
from city_whole_strategy_policy import CityWholeStrategyFeatures
from city_strategy_policy import CityStrategyFeatures, STRATEGY_CONTEXT
from city_road_policy import ROAD_SLOTS
from city_wait_choice_policy import CityRoadHeadsAfterWaitPolicy


class CityIndependentRoadFeatures(CityWholeStrategyFeatures):
    def __init__(self, observation_space, **kwargs):
        super().__init__(observation_space, **kwargs)
        # Migration explicitly populates this copy from the source encoder.
        # It is excluded from the optimizer and stays frozen in native training.
        self.growth_wait_spatial = deepcopy(self.growth_strategy_spatial)
        self.growth_wait_spatial.requires_grad_(False)

    @staticmethod
    def pool(spatial, visible):
        count = visible.sum((2, 3))
        mean = (spatial*visible).sum((2, 3))/count.clamp_min(1)
        maximum = spatial.masked_fill(~visible, torch.finfo(spatial.dtype).min).amax((2, 3))
        maximum = torch.where(count > 0, maximum, torch.zeros_like(maximum))
        return torch.cat((mean, maximum), dim=1)

    def _forward_uncached(self, observations):
        base = CityStrategyFeatures.forward(self, observations)
        context = base[:, -STRATEGY_CONTEXT:]
        gate = self.strategy_gate(context[:, 57:58])
        grid = observations['grid']
        visible = grid[:, :1] > 0
        road_spatial = self.growth_strategy_spatial(grid)
        with torch.no_grad():
            wait_spatial = self.growth_wait_spatial(grid)
        pooled_road = self.pool(road_spatial, visible)
        pooled_wait = self.pool(wait_spatial, visible)
        roads = self.growth_strategy_spatial_roads(road_spatial).permute(0, 2, 3, 1).reshape(-1, ROAD_SLOTS)*gate
        wait = self.growth_strategy_visual_wait(pooled_wait)*gate
        index = ROAD_SLOTS+self.context_width
        return torch.cat((base[:, :ROAD_SLOTS]+roads, base[:, ROAD_SLOTS:index],
                          base[:, index:index+1]+wait, base[:, index+1:], pooled_road), dim=1)


class CityRoadSpatialAfterWaitPolicy(CityRoadHeadsAfterWaitPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        if not isinstance(self.features_extractor, CityIndependentRoadFeatures):
            raise ValueError('Trainable road encoder requires a separate preserved Wait encoder')
        self.features_extractor.growth_strategy_spatial.requires_grad_(True)
