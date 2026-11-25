"""Destination-specific service features for already visible city roads."""

import torch
from torch import nn

from city_growth_policy import CityGrowthFeatures, CityGrowthPolicy
from city_road_policy import ROAD_SLOTS
from city_service_policy import CityServiceFeatures
from midgame_timing_policy import MidgameTimingFeatures
from visible_observation import CELLS, HEIGHT, WIDTH


class CityNetworkServiceFeatures(CityServiceFeatures):
    def __init__(self, observation_space, *, conservative=True):
        super().__init__(observation_space, conservative=conservative)
        self.growth_service_urgency = nn.Parameter(torch.tensor(0.))
        self.register_buffer('reverse_direction', (torch.arange(8) + 4) % 8, persistent=False)
        self.register_buffer('on_board_edges', self.neighbors[:CELLS, :4].flatten() < CELLS, persistent=False)

    def component_labels(self, links):
        """Union neighboring cells over reciprocal built edges to a fixed point."""
        cells = torch.arange(CELLS+1, device=links.device)
        labels = cells.expand(len(links), -1)
        while True:
            neighbor = labels[:, self.neighbors].masked_fill(~links, CELLS)
            candidate = torch.minimum(labels, neighbor.amin(dim=2))
            roots = labels.clone().scatter_reduce_(1, labels, candidate, reduce='amin')
            joined = roots.gather(1, labels)
            if torch.equal(joined, labels):
                return labels
            # Shorten chains of components joined in this round.
            while True:
                parent = joined.gather(1, joined)
                if torch.equal(parent, joined):
                    break
                joined = parent
            labels = joined

    def visible_components(self, grid, directions, approaches):
        visible = grid[:, 0].bool()
        road_cell = visible & grid[:, 18].bool()
        links = torch.nn.functional.pad(grid[:, 9:17].transpose(1, 2).bool(), (0, 0, 0, 1))
        reciprocal = links[:, self.neighbors, self.reverse_direction]
        eligible = torch.nn.functional.pad(road_cell, (0, 1))
        ordinary_links = links & reciprocal & eligible[:, :, None] & eligible[:, self.neighbors]
        labels = self.component_labels(ordinary_links)

        # Prospective approaches can be empty land. Service needs an actual
        # reciprocal driveway link at each end of an existing component.
        open_approach = torch.nn.functional.pad(road_cell & grid[:, 1].bool(), (0, 1)).gather(1, approaches)
        parcel_link = links[:, :CELLS].gather(2, directions[..., None]).squeeze(2)
        reciprocal_link = links[
            torch.arange(len(grid), device=grid.device)[:, None],
            approaches, self.reverse_direction[directions],
        ]
        attached = open_approach & parcel_link & reciprocal_link
        return labels, open_approach, attached

    @staticmethod
    def roots_by_color(root, colors, parcels):
        active = colors & parcels[:, None]
        values = torch.zeros((len(root), 8, CELLS+1), dtype=torch.float32, device=root.device)
        indices = root[:, None].expand(-1, 8, -1)
        return values.scatter_reduce_(2, indices, active.float(), reduce='amax').bool()

    @staticmethod
    def local_distance(region):
        reach = region.reshape(-1, 1, HEIGHT, WIDTH).float()
        distance = 1. - reach
        for _ in range(5):
            reach = torch.nn.functional.max_pool2d(reach, 3, stride=1, padding=1)
            distance = distance + 1. - reach
        return distance.flatten(1)

    def destination_edges(self, grid, labels, home, target_roots, pending):
        advance = grid.new_zeros((len(grid), ROAD_SLOTS))
        joins = torch.zeros_like(advance)
        urgency = torch.zeros_like(advance)
        # Process visible entrances individually so a near shop does not erase
        # progress toward a different shop with the same color.
        targets = pending.nonzero()
        if not len(targets):
            return advance, joins, urgency
        home_distance = self.local_distance(home.flatten(0, 1)).reshape(len(grid), 8, CELLS)
        for group in targets.split(64):
            batch, color, parcel = group.unbind(1)
            matching_home = home[batch, color]
            matched_shop = labels[batch, :CELLS] == target_roots[batch, parcel, None]
            to_shop = self.local_distance(matched_shop)
            to_home = home_distance[batch, color]
            gap = to_shop.masked_fill(~matching_home, 6).amin(dim=1, keepdim=True)
            hp, hq = matching_home[:, self.starts], matching_home[:, self.ends]
            sp, sq = matched_shop[:, self.starts], matched_shop[:, self.ends]
            matched = (hp & sq) | (hq & sp)
            forward = torch.maximum(
                (gap-to_shop[:, self.ends]).clamp(0, 1) * (hp & ~hq),
                (gap-to_shop[:, self.starts]).clamp(0, 1) * (hq & ~hp),
            )
            backward = torch.maximum(
                (gap-to_home[:, self.ends]).clamp(0, 1) * (sp & ~sq),
                (gap-to_home[:, self.starts]).clamp(0, 1) * (sq & ~sp),
            )
            progresses = torch.maximum(torch.maximum(forward, backward) * (gap < 6), matched)
            need = grid[batch, 41, parcel, None] + grid[batch, 42, parcel, None]
            index = batch[:, None].expand_as(progresses)
            advance.scatter_reduce_(0, index, progresses, reduce='amax')
            joins.scatter_reduce_(0, index, matched.float(), reduce='amax')
            urgency.scatter_reduce_(0, index, need * progresses, reduce='amax')
        return advance, joins, urgency

    def service_features(self, raw_grid):
        grid = raw_grid.flatten(2)
        colors = grid[:, 21:29].bool()
        entrance = grid[:, 29].bool()
        houses = grid[:, 19].bool() & entrance
        shops = grid[:, 20].bool() & entrance
        directions = grid[:, 30:38].argmax(dim=1)
        approaches = self.neighbors[self.service_cells, directions]
        labels, open_approach, attached = self.visible_components(grid, directions, approaches)
        roots = labels.gather(1, approaches)
        homes = self.roots_by_color(roots, colors, houses & open_approach)
        connected_homes = self.roots_by_color(roots, colors, houses & attached)
        already_connected = connected_homes.gather(2, roots[:, None].expand(-1, 8, -1))
        served = colors & (shops & attached)[:, None] & already_connected
        matching_color = (colors & houses[:, None]).any(dim=2, keepdim=True)
        pending = colors & shops[:, None] & matching_color & ~served
        home_regions = homes.gather(2, labels[:, None, :CELLS].expand(-1, 8, -1))
        advance, joins, urgency = self.destination_edges(
            grid, labels, home_regions, roots, pending & open_approach[:, None],
        )
        advance = advance * self.on_board_edges
        joins = joins * self.on_board_edges
        urgency = urgency * self.on_board_edges
        multiple = (houses | shops).sum(dim=1, keepdim=True) > 2
        active = multiple & advance.bool().any(dim=1, keepdim=True)
        established = multiple & served.flatten(1).any(dim=1, keepdim=True)
        quiet = ~pending.flatten(1).any(dim=1, keepdim=True) & ~grid[:, 42].bool().any(dim=1, keepdim=True)
        return advance, joins, urgency, active, established, quiet

    def forward(self, observations):
        features = CityGrowthFeatures.forward(self, observations)
        with torch.no_grad():
            advance, joins, urgency, available, established, quiet = self.service_features(observations['grid'])
            later = features[:, -1:] == 0
            active = later & available
            reserve = later & established
            closed = later & MidgameTimingFeatures.waiting_context(self, observations['grid'])
            if self.conservative:
                reserve = reserve & quiet & (observations['global'][:, :1] <= 8./108.)
        evidence = advance * active
        roads = evidence * self.growth_service_progress
        roads = roads + active * (joins * self.growth_service_join + urgency * self.growth_service_urgency)
        wait = self.growth_service_blocked * (closed & ~active)
        wait = wait + self.growth_service_reserve * (reserve & ~active)
        wait_index = ROAD_SLOTS + self.context_width
        coupling = self.growth_service_coupling * (active if self.conservative else later & established)
        return torch.cat((
            features[:, :ROAD_SLOTS] + roads,
            features[:, ROAD_SLOTS:wait_index],
            features[:, wait_index:wait_index+1] + wait,
            features[:, wait_index+1:-1] + evidence,
            features[:, -1:] + coupling,
        ), dim=1)


class CityNetworkServicePolicy(CityGrowthPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.features_extractor.named_parameters():
            parameter.requires_grad_(name.startswith('growth_service_'))
        self.optimizer = self.optimizer_class(
            filter(lambda parameter: parameter.requires_grad, self.parameters()),
            lr=lr_schedule(1), **self.optimizer_kwargs,
        )
