"""Checkpoint-specific softening of road preferences in established networks.

Only relative road logits change. Wait-versus-build mass keeps the existing
masked normalization, and unestablished states use the exact frozen reference.
The temperature is generic exploration, not a preferred-edge label.
"""
import torch
from city_established_policy import CityEstablishedFeatures
from city_network_service_policy import CityNetworkServiceFeatures
from city_road_policy import ROAD_SLOTS


class CityExplorationFeatures(CityEstablishedFeatures):
    def __init__(self, observation_space, *, conservative=True, temperature=8.):
        if not 1 <= temperature <= 20:
            raise ValueError('Road temperature must be between 1 and 20')
        super().__init__(observation_space, conservative=conservative)
        self.register_buffer('growth_road_temperature',torch.tensor(float(temperature)))

    def forward(self, observations):
        with torch.no_grad():
            established=self.service_features(observations['grid'])[-2]
            opening=self.opening_reference(observations)
        growing=CityNetworkServiceFeatures.forward(self,observations)
        growing=torch.cat((growing[:,:ROAD_SLOTS]/self.growth_road_temperature,
                           growing[:,ROAD_SLOTS:]),dim=1)
        return torch.where(established,growing,opening)


class CityResidualExplorationFeatures(CityExplorationFeatures):
    """Soften the frozen road prior while leaving learned corrections unscaled."""
    def forward(self, observations):
        with torch.no_grad():
            established=self.service_features(observations['grid'])[-2]
            opening=self.opening_reference(observations)
        growing=CityNetworkServiceFeatures.forward(self,observations)
        roads=(opening[:,:ROAD_SLOTS]/self.growth_road_temperature
               + growing[:,:ROAD_SLOTS]-opening[:,:ROAD_SLOTS])
        growing=torch.cat((roads,growing[:,ROAD_SLOTS:]),dim=1)
        return torch.where(established,growing,opening)
