"""Learn road priorities from matching visible parcels and existing road components."""

import torch
from torch import nn

from city_growth_policy import CityGrowthFeatures
from city_road_policy import ROAD_SLOTS
from midgame_timing_policy import MidgameTimingFeatures
from visible_observation import CELLS, HEIGHT, WIDTH


class CityServiceFeatures(CityGrowthFeatures):
    def __init__(self, observation_space, *, conservative=False):
        super().__init__(observation_space)
        self.conservative = conservative
        self.growth_service_progress = nn.Parameter(torch.tensor(0. if conservative else 3.5))
        self.growth_service_join = nn.Parameter(torch.tensor(.8 if conservative else 2.5))
        self.growth_service_coupling = nn.Parameter(torch.tensor(0. if conservative else 1.8))
        self.growth_service_blocked = nn.Parameter(torch.tensor(5.0))
        self.growth_service_reserve = nn.Parameter(torch.tensor(1.6 if conservative else .45))
        self.register_buffer('service_cells', torch.arange(CELLS), persistent=False)

    def driveway_anchors(self, grid, parcels):
        directions = grid[:, 30:38].argmax(dim=1)
        approach = self.neighbors[self.service_cells, directions]
        valid = approach < CELLS
        seen = grid[:, 0].bool().gather(1, approach.clamp_max(CELLS-1))
        traversable = grid[:, 1].bool().gather(1, approach.clamp_max(CELLS-1))
        eligible = (valid & seen & traversable)[:, None] & parcels
        indices = approach[:, None].expand(-1, 8, -1)
        anchors = torch.zeros((len(grid), 8, CELLS+1), device=grid.device, dtype=grid.dtype)
        anchors.scatter_reduce_(2, indices, eligible.to(grid.dtype), reduce='amax', include_self=True)
        return anchors.bool()

    def connected_roads(self, anchors, links):
        current = anchors
        for _ in range(10):
            current = current | (current[:, :, self.neighbors] & links[:, None]).any(dim=-1)
        return current

    def separation(self, region):
        reach = region[:, :, :CELLS].reshape(-1, 8, HEIGHT, WIDTH).float()
        distance = 1. - reach
        for _ in range(4):
            reach = torch.nn.functional.max_pool2d(reach, 3, stride=1, padding=1)
            distance = distance + 1. - reach
        return distance.flatten(2)

    def service_evidence(self, raw_grid):
        grid = raw_grid.flatten(2)
        colors = grid[:, 21:29].bool()
        entrance = grid[:, 29].bool()
        houses = colors & (grid[:, 19].bool() & entrance)[:, None]
        destinations = colors & (grid[:, 20].bool() & entrance)[:, None]
        links = torch.nn.functional.pad(grid[:, 9:17].transpose(1, 2).bool(), (0, 0, 0, 1))

        home = self.connected_roads(self.driveway_anchors(grid, houses), links)
        target = self.driveway_anchors(grid, destinations)
        established = (home & target).flatten(1).any(dim=1, keepdim=True)
        pending = target & ~home & home.any(dim=2, keepdim=True)
        shop = self.connected_roads(pending, links)
        from_home, from_shop = self.separation(home), self.separation(shop)
        gap = from_shop.masked_fill(~home[:, :, :CELLS], 5).amin(dim=2, keepdim=True)
        active = established & ((gap < 5) & pending.any(dim=2, keepdim=True)).any(dim=1)

        home_start, home_end = home[:, :, self.starts], home[:, :, self.ends]
        shop_start, shop_end = shop[:, :, self.starts], shop[:, :, self.ends]
        advance = torch.maximum(
            (gap - from_shop[:, :, self.ends]).clamp(0, 1) * (home_start & ~home_end),
            (gap - from_shop[:, :, self.starts]).clamp(0, 1) * (home_end & ~home_start),
        )
        advance = torch.maximum(advance, torch.maximum(
            (gap - from_home[:, :, self.ends]).clamp(0, 1) * (shop_start & ~shop_end),
            (gap - from_home[:, :, self.starts]).clamp(0, 1) * (shop_end & ~shop_start),
        ))
        joins = ((home_start & shop_end) | (home_end & shop_start)).any(dim=1)
        multiple = (houses | destinations).sum(dim=(1, 2), keepdim=False)[:, None] > 2
        # Unseen or blocked driveway approaches remain unresolved for this gate.
        reached = torch.nn.functional.pad(home[:, :, :CELLS], (0, 1), value=False)
        directions = grid[:, 30:38].argmax(dim=1)
        approaches = self.neighbors[self.service_cells, directions]
        at_door = reached.gather(2, approaches[:, None].expand(-1, 8, -1))
        pending_destinations = destinations & home.any(dim=2, keepdim=True) & ~at_door
        quiet = ~pending_destinations.flatten(1).any(dim=1, keepdim=True)
        quiet &= ~grid[:, 42].bool().any(dim=1, keepdim=True)
        return advance.amax(dim=1), joins, active & multiple, established & multiple, quiet

    def forward(self, observations):
        features = super().forward(observations)
        with torch.no_grad():
            advance, joins, available, established, quiet = self.service_evidence(observations['grid'])
            later = features[:, -1:] == 0
            active = later & available
            reserve = later & established
            closed = later & MidgameTimingFeatures.waiting_context(self, observations['grid'])
            if self.conservative:
                scarce = observations['global'][:, :1] <= 8./108.
                reserve = reserve & quiet & scarce
        wait_index = ROAD_SLOTS + self.context_width
        evidence = torch.maximum(advance, joins.to(advance.dtype)) * active
        roads = self.growth_service_progress * evidence + self.growth_service_join * (joins & active)
        wait = self.growth_service_blocked * (closed & ~active)
        wait = wait + self.growth_service_reserve * (reserve & ~active)
        if self.conservative:
            # Calibrate immediate joins separately from holding stock.
            waits_for_road = active
        else:
            waits_for_road = reserve
        # The existing learned distribution pools priority only over native-legal roads.
        base_evidence = features[:, wait_index+1:-1]
        return torch.cat((
            features[:, :ROAD_SLOTS] + roads,
            features[:, ROAD_SLOTS:wait_index],
            features[:, wait_index:wait_index+1] + wait,
            base_evidence + evidence,
            features[:, -1:] + self.growth_service_coupling * waits_for_road,
        ), dim=1)
