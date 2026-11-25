"""A soft city Wait correction for visibly blocked destination approaches."""

import torch
from torch import nn

from city_growth_policy import CityGrowthFeatures, CityGrowthPolicy
from city_road_policy import ROAD_SLOTS
from visible_observation import CELLS


class MidgameTimingFeatures(CityGrowthFeatures):
    def __init__(self, observation_space):
        super().__init__(observation_space)
        self.growth_service_wait = nn.Parameter(torch.tensor(8.))

    def waiting_context(self, grid):
        grid = grid.flatten(2)
        colors = grid[:, 21:29].bool()
        houses = grid[:, 19].bool()
        matching_colors = (colors & houses[:, None]).any(dim=2)
        matching_shops = (colors & matching_colors[:, :, None]).any(dim=1) & grid[:, 20].bool()
        entrances = matching_shops & grid[:, 29].bool()
        driveway = grid[:, 30:38]
        attached = (driveway * grid[:, 9:17]).sum(dim=1).bool()
        pending = entrances & ~attached
        direction = driveway.argmax(dim=1)
        cells = torch.arange(CELLS, device=grid.device)
        approach = self.neighbors[cells, direction].clamp_max(CELLS-1)
        blocked = grid[:, 3].gather(1, approach).bool()
        # Prefer Wait only when there is an established connection and all
        # unmatched road approaches for the currently visible pairs are blocked.
        established = (entrances & attached).any(dim=1)
        waiting_for_opening = (pending & blocked).any(dim=1) & ~(pending & ~blocked).any(dim=1)
        return (established & waiting_for_opening)[:, None]

    def forward(self, observations):
        with torch.no_grad():
            base = super().forward(observations)
        wait_index = ROAD_SLOTS + self.context_width
        later_city = base[:, -1:] == 0
        bonus = self.growth_service_wait * (later_city & self.waiting_context(observations['grid']))
        return torch.cat((base[:, :wait_index], base[:, wait_index:wait_index+1] + bonus,
                          base[:, wait_index+1:]), dim=1)


class MidgameTimingPolicy(CityGrowthPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.features_extractor.named_parameters():
            parameter.requires_grad_(name == 'growth_service_wait')
        self.optimizer = self.optimizer_class(
            filter(lambda parameter: parameter.requires_grad, self.parameters()),
            lr=lr_schedule(1), **self.optimizer_kwargs,
        )
