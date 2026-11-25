"""Masked PPO actor and critic for the native city's road and Wait actions."""

import torch
from sb3_contrib.common.maskable.distributions import MaskableCategoricalDistribution
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from torch import nn

from edge_policy import TILE_CHANNELS, LocalEdgeFeatures, EdgeActionHead
from environment import DIRS
from visible_observation import CELLS, HEIGHT, WIDTH

ROAD_SLOTS = CELLS * 4
CONTEXT_CHANNELS = 16


class CityEdgeFeatures(LocalEdgeFeatures):
    """Evaluate the practice endpoint and edge networks on the full city canvas."""

    def __init__(self, observation_space):
        super().__init__(observation_space)
        cells = torch.arange(CELLS)
        directions = torch.tensor(DIRS)
        x = cells[:, None] % WIDTH + directions[:, 0]
        y = cells[:, None] // WIDTH + directions[:, 1]
        inside = (x >= 0) & (x < WIDTH) & (y >= 0) & (y < HEIGHT)
        neighbors = torch.where(inside, y * WIDTH + x, CELLS)
        self.neighbors = torch.cat((neighbors, torch.full((1, 8), CELLS)))
        canonical = torch.arange(4)
        self.endpoint_views = torch.stack((
            cells[:, None] * 8 + canonical, neighbors[:, :4] * 8 + canonical + 4,
        ), dim=-1).reshape(ROAD_SLOTS, 2)
        channels = observation_space['grid'].shape[0]
        global_width = observation_space['global'].shape[0]
        self.context_width = 2 * CONTEXT_CHANNELS + global_width
        self._features_dim = ROAD_SLOTS + self.context_width
        self.road_score = EdgeActionHead().score
        self.context = nn.Sequential(
            nn.Conv2d(channels, CONTEXT_CHANNELS, 1), nn.SiLU(),
            nn.Conv2d(CONTEXT_CHANNELS, CONTEXT_CHANNELS, 3, padding=2, dilation=2), nn.SiLU(),
        )
        self.road_context = nn.Linear(self.context_width, CONTEXT_CHANNELS)
        self.road_residual = nn.Conv2d(CONTEXT_CHANNELS, 4, 1)
        nn.init.zeros_(self.road_residual.weight)
        nn.init.zeros_(self.road_residual.bias)

    def local_scores(self, board):
        tiles = board[:, (*TILE_CHANNELS, *range(9, 17), *range(30, 38))].flatten(2).transpose(1, 2)
        tiles = torch.cat((tiles, tiles.new_zeros((len(tiles), 1, tiles.shape[-1]))), dim=1)
        scalars = tiles[..., :len(TILE_CHANNELS)]
        links, driveways = tiles[..., len(TILE_CHANNELS):].split(8, dim=-1)
        road_neighbors = scalars[:, self.neighbors, TILE_CHANNELS.index(5)]
        oriented = torch.cat((
            scalars[:, :, None].expand(-1, -1, 8, -1),
            links[:, :, self.relative_directions],
            driveways[:, :, self.relative_directions],
            road_neighbors[:, :, self.relative_directions],
        ), dim=-1)
        # Encode each oriented endpoint once before reusing it in edge pairs.
        endpoints = self.endpoint(oriented).flatten(1, 2)[:, self.endpoint_views]
        first, second = endpoints.unbind(dim=2)
        edges = self.edge(torch.cat((first + second, (first - second).abs()), dim=-1))
        return self.road_score(edges).squeeze(-1)

    def forward(self, observations):
        board = observations['grid']
        context = self.context(board)
        visible = board[:, :1] > 0
        pooled = torch.cat((
            (context * visible).sum(dim=(2, 3)) / visible.sum(dim=(2, 3)).clamp_min(1),
            context.masked_fill(~visible, torch.finfo(context.dtype).min).amax(dim=(2, 3)),
            observations['global'],
        ), dim=1)
        residual = self.road_residual(torch.nn.functional.silu(
            context + self.road_context(pooled)[:, :, None, None]
        )).permute(0, 2, 3, 1).reshape(-1, ROAD_SLOTS)
        return torch.cat((self.local_scores(board) + residual, pooled), dim=1)


class CityLatents(nn.Module):
    def forward_actor(self, features):
        return features

    def forward_critic(self, features):
        return features[:, ROAD_SLOTS:]

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class CityActionHead(nn.Module):
    def __init__(self, context_width):
        super().__init__()
        self.wait = nn.Sequential(nn.Linear(context_width, 32), nn.SiLU(), nn.Linear(32, 1))
        nn.init.zeros_(self.wait[-1].weight)
        nn.init.zeros_(self.wait[-1].bias)

    def forward(self, features):
        return torch.cat((self.wait(features[:, ROAD_SLOTS:]), features[:, :ROAD_SLOTS]), dim=1)


class CityActionDistribution(MaskableCategoricalDistribution):
    """Put Wait and all legal roads on equal footing before choosing a road."""

    def proba_distribution(self, action_logits):
        self.raw_logits = action_logits
        self.apply_masking(None)
        return self

    def apply_masking(self, masks):
        wait, roads = self.raw_logits.split((1, ROAD_SLOTS), dim=1)
        if masks is None:
            legal_roads = torch.ones_like(roads, dtype=torch.bool)
        else:
            legal_roads = torch.as_tensor(masks, dtype=torch.bool, device=roads.device)
            legal_roads = legal_roads.reshape_as(self.raw_logits)[:, 1:]
        has_road = legal_roads.any(dim=1, keepdim=True)
        # Avoid logsumexp of an empty set during both inference and backpropagation.
        normalizer = roads.masked_fill(~legal_roads & has_road, -torch.inf).logsumexp(dim=1, keepdim=True)
        super().proba_distribution(torch.cat((wait, roads - normalizer), dim=1))
        super().apply_masking(masks)


class CityRoadPolicy(MaskableActorCriticPolicy):
    def _build(self, lr_schedule):
        if self.action_space.n != ROAD_SLOTS + 1 or not self.share_features_extractor:
            raise ValueError('The city policy requires the full city action space and shared features')
        context_width = self.features_extractor.context_width
        self.action_dist = CityActionDistribution(self.action_space.n)
        self.mlp_extractor = CityLatents()
        self.action_net = CityActionHead(context_width)
        self.value_net = nn.Sequential(nn.Linear(context_width, 64), nn.SiLU(), nn.Linear(64, 1))
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


def transfer_construction(parent_policy, city_policy):
    """Copy the three shared construction modules using strict shape checks."""
    source = parent_policy.state_dict()
    extractor = city_policy.features_extractor
    modules = {
        'features_extractor.endpoint': extractor.endpoint,
        'features_extractor.edge': extractor.edge,
        'action_net.draw.base.score': extractor.road_score,
    }
    copied = []
    for prefix, target in modules.items():
        state = {name: source[f'{prefix}.{name}'] for name in target.state_dict()}
        target.load_state_dict(state, strict=True)
        copied.extend(f'{prefix}.{name}' for name in state)
    return copied
