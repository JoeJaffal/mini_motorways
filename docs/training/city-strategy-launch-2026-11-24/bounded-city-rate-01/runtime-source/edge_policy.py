"""Shared local actor for one-build practice, using only visible board channels."""
import hashlib
from pathlib import Path

import torch
from torch import nn
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from connection_practice import ARENA_SIZE
from environment import DIRS
from hierarchy_policy import practice_policy
from visible_observation import WIDTH


EDGE_POLICY = 'shared-edge'
BOARD_POLICY = 'board'
TILES = ARENA_SIZE ** 2
EDGE_SLOTS = TILES * 4
EDGE_WIDTH = 48
# Revealed tile, ordinary road, house, destination, designated entrance.
TILE_CHANNELS = (0, 5, 19, 20, 29)


class LocalEdgeFeatures(BaseFeaturesExtractor):
    def __init__(self, observation_space):
        super().__init__(observation_space, features_dim=EDGE_SLOTS * EDGE_WIDTH)
        x = torch.arange(TILES) % ARENA_SIZE
        y = torch.arange(TILES) // ARENA_SIZE
        directions = torch.tensor(DIRS)
        nx = x[:, None] + directions[:, 0]
        ny = y[:, None] + directions[:, 1]
        in_arena = (nx >= 0) & (nx < ARENA_SIZE) & (ny >= 0) & (ny < ARENA_SIZE)
        neighbors = torch.where(in_arena, ny * ARENA_SIZE + nx, TILES)
        neighbors = torch.cat((neighbors, torch.full((1, 8), TILES)), dim=0)

        # The first four directions are the environment's canonical edge IDs.
        # Both endpoint views face into the candidate edge.
        canonical = torch.arange(4)
        source_view = torch.arange(TILES)[:, None] * 8 + canonical
        target_view = neighbors[:TILES, :4] * 8 + (canonical + 4)
        endpoint_views = torch.stack((source_view, target_view), dim=-1).reshape(EDGE_SLOTS, 2)
        self.register_buffer('canvas_offsets', y * WIDTH + x, persistent=False)
        self.register_buffer('neighbors', neighbors, persistent=False)
        self.register_buffer('endpoint_views', endpoint_views, persistent=False)
        self.register_buffer('relative_directions', (torch.arange(8)[:, None] + torch.arange(8)) % 8,
                             persistent=False)

        # Per endpoint: tile properties, link directions, driveway directions,
        # and road presence at the eight neighboring offsets.
        self.endpoint = nn.Sequential(nn.Linear(len(TILE_CHANNELS) + 24, 32), nn.SiLU())
        self.edge = nn.Sequential(nn.Linear(64, EDGE_WIDTH), nn.SiLU())

    def forward(self, observations):
        board = observations['grid']
        visible = board[:, 0]
        ymin = visible.amax(dim=2).argmax(dim=1)
        xmin = visible.amax(dim=1).argmax(dim=1)
        indices = ymin[:, None] * WIDTH + xmin[:, None] + self.canvas_offsets
        selected = board[:, (*TILE_CHANNELS, *range(9, 17), *range(30, 38)), :, :].flatten(2)
        tiles = selected.gather(2, indices[:, None].expand(-1, selected.shape[1], -1)).transpose(1, 2)
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
        endpoints = oriented.flatten(1, 2)[:, self.endpoint_views]
        endpoints = self.endpoint(endpoints)
        first, second = endpoints.unbind(dim=2)
        # Canonical endpoint order can reverse after a board rotation.
        edge = self.edge(torch.cat((first + second, (first - second).abs()), dim=-1))
        return edge.flatten(1)


class EdgeLatents(nn.Module):
    def forward_actor(self, features):
        return features.reshape(-1, EDGE_SLOTS, EDGE_WIDTH)

    def forward_critic(self, features):
        edges = self.forward_actor(features)
        return torch.cat((edges.mean(dim=1), edges.amax(dim=1)), dim=-1)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)


class EdgeActionHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.score = nn.Linear(EDGE_WIDTH, 1)

    def forward(self, edges):
        scores = self.score(edges).squeeze(-1)
        # Keep the common interface's slot zero. The single-build mask hides it.
        return torch.cat((scores.new_zeros((len(scores), 1)), scores), dim=1)


class SharedEdgePolicy(MaskableActorCriticPolicy):
    def _build(self, lr_schedule):
        self.mlp_extractor = EdgeLatents()
        self.action_net = EdgeActionHead()
        self.value_net = nn.Sequential(nn.Linear(2 * EDGE_WIDTH, 32), nn.SiLU(), nn.Linear(32, 1))
        self.features_extractor.apply(lambda layer: self.init_weights(layer, gain=2 ** .5))
        self.value_net.apply(lambda layer: self.init_weights(layer, gain=1.))
        self.init_weights(self.action_net.score, gain=.01)
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)


def stage1_policy(env, lr_schedule, *, name=BOARD_POLICY):
    if name == BOARD_POLICY:
        return practice_policy(env, lr_schedule)
    if name != EDGE_POLICY or not env.single_build or env.action_space.n != EDGE_SLOTS + 1:
        raise ValueError('The shared edge policy requires one-gap-single-build')
    return SharedEdgePolicy(
        env.observation_space, env.action_space, lr_schedule,
        features_extractor_class=LocalEdgeFeatures, normalize_images=False,
        optimizer_kwargs={'eps': 1e-5},
    )


def checkpoint_policy(env, lr_schedule, config):
    name = config.get('policy', BOARD_POLICY)
    if name == EDGE_POLICY:
        actual = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if config['source_hashes'].get('edge_policy.py') != actual:
            raise ValueError('Shared edge policy source differs')
    return stage1_policy(env, lr_schedule, name=name)
