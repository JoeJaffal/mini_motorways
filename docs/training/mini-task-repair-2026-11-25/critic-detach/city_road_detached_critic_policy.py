"""Let PPO's actor train road features without value-loss feature updates.

The critic still learns its value head from the current features. This is a
stop-gradient experiment, not a separate learned critic encoder.
"""
from city_road_choice_policy import CityRoadChoicePolicy
from city_wide_strategy_policy import WideStrategyLatents


class DetachedWideStrategyLatents(WideStrategyLatents):
    def forward_critic(self, features):
        return super().forward_critic(features).detach()


class CityRoadChoiceDetachedCriticPolicy(CityRoadChoicePolicy):
    critic_features_detached = True

    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        # Parameter-free replacement: outputs, weights and named Adam states
        # remain compatible; only the critic's gradient path changes.
        self.mlp_extractor = DetachedWideStrategyLatents()
