"""One learned city correction active during both opening and expansion."""
import torch
from city_wide_strategy_policy import CityWideStrategyFeatures, CityWideStrategyPolicy

class CityWholeStrategyFeatures(CityWideStrategyFeatures):
    def strategy_gate(self, established):
        return torch.ones_like(established)

class CityWholeStrategyPolicy(CityWideStrategyPolicy):
    pass
