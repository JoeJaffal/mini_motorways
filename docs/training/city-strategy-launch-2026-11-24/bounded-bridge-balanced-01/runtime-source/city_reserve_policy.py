"""PPO learns when to spend stock; inherited conditional road choices stay fixed."""
import torch
from torch import nn
from city_relational_policy import CitySharpRelationsFeatures, RelativeRateAdam
from city_growth_policy import CityGrowthPolicy
from city_road_policy import ROAD_SLOTS
from midgame_timing_policy import MidgameTimingFeatures


class CityReserveFeatures(CitySharpRelationsFeatures):
    def __init__(self, observation_space, **kwargs):
        super().__init__(observation_space, **kwargs)
        self.growth_reserve_wait = nn.Linear(6, 1, bias=False)
        nn.init.zeros_(self.growth_reserve_wait.weight)

    def reserve_evidence(self, observations):
        _, _, _, available, established, quiet = self.service_features(observations['grid'])
        # Native inventory is encoded as stock/(stock+100); undo that visible
        # normalization, then saturate at eight roads for this bounded context.
        encoded = observations['global'][:, :1]
        stock = (100*encoded/(1-encoded).clamp_min(.01)/8).clamp(0, 1)
        quiet = quiet.float(); active = available.float()
        blocked = 1-torch.maximum(quiet,active)
        features = torch.cat((quiet, quiet*stock, active, active*stock, blocked, blocked*stock), dim=1)
        return features*established

    def forward(self, observations):
        with torch.no_grad():
            base = super().forward(observations)
            evidence = self.reserve_evidence(observations)
        index = ROAD_SLOTS+self.context_width
        return torch.cat((base[:, :index], base[:, index:index+1]+self.growth_reserve_wait(evidence), base[:, index+1:]), dim=1)


class CityReservePolicy(CityGrowthPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        for name, parameter in self.features_extractor.named_parameters():
            parameter.requires_grad_(name.startswith('growth_reserve_wait.'))
        self.optimizer = RelativeRateAdam([
            dict(params=list(self.features_extractor.growth_reserve_wait.parameters()), lr_scale=1.),
            dict(params=list(self.value_net.parameters()), lr_scale=.01),
        ], lr=lr_schedule(1), **self.optimizer_kwargs)


class CityVisibleReserveFeatures(CityReserveFeatures):
    """Missing local progress is not evidence that construction must wait.

    Preserve the first experiment's class for old checkpoints. This repair
    limits its last two inputs to actually visible blocked shop approaches.
    """
    def reserve_evidence(self, observations):
        evidence = super().reserve_evidence(observations)
        blocked = MidgameTimingFeatures.waiting_context(self, observations['grid'])
        return torch.cat((evidence[:, :4], evidence[:, 4:]*blocked), dim=1)
