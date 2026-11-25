"""Preserve the retained actor until a matching network exists on a growing city.

The reference must be copied from the retained checkpoint during preparation.
The gate is the visible service graph (including the existing >2-parcel gate),
not a delivery counter. This deliberately freezes unsuccessful openings too;
opening improvements require a separately validated reference replacement.
"""

import torch
from city_network_service_policy import CityNetworkServiceFeatures


class CityEstablishedFeatures(CityNetworkServiceFeatures):
    def __init__(self, observation_space, *, conservative=True):
        super().__init__(observation_space, conservative=conservative)
        self.opening_reference = CityNetworkServiceFeatures(observation_space, conservative=conservative)
        self.opening_reference.requires_grad_(False)

    def forward(self, observations):
        with torch.no_grad():
            established = self.service_features(observations['grid'])[-2]
            opening = self.opening_reference(observations)
        growing = super().forward(observations)
        return torch.where(established, growing, opening)
