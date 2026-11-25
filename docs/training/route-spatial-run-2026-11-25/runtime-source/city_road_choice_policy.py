"""Diagnostic whole-city policy with frozen, zero-output Wait corrections."""
from city_whole_strategy_policy import CityWholeStrategyPolicy
from city_relational_policy import RelativeRateAdam


class CityRoadChoicePolicy(CityWholeStrategyPolicy):
    """Train road preferences and critic; initialization must have zero Wait heads.

    The shared spatial encoder remains trainable. Consequently the visual Wait
    head must retain a zero final layer to keep Wait invariant on shared states.
    Use zero-residual initialization or an explicit migration that restores and
    verifies both zero-output Wait modules. Blind conversion of an arbitrary
    trained joint policy does not guarantee invariant Wait behavior.
    """
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        f = self.features_extractor
        for module in (f.growth_strategy_wait, f.growth_strategy_visual_wait):
            module.requires_grad_(False)
        self.optimizer = RelativeRateAdam([
            dict(params=[*f.growth_strategy_roads.parameters(),
                         *f.growth_strategy_spatial_roads.parameters()], lr_scale=.3),
            dict(params=list(f.growth_strategy_spatial.parameters()), lr_scale=.1),
            dict(params=list(self.value_net.parameters()), lr_scale=.1),
        ], lr=lr_schedule(1), **self.optimizer_kwargs)
