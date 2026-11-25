"""PPO Wait corrections with retained, frozen conditional road skills."""
import torch
from city_whole_strategy_policy import CityWholeStrategyPolicy
from city_road_detached_critic_policy import DetachedWideStrategyLatents


class CityWaitChoicePolicy(CityWholeStrategyPolicy):
    """Keep all optimizer groups so previously learned Adam states survive."""
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = DetachedWideStrategyLatents()
        self.requires_grad_(False)
        for name in ('growth_strategy_wait', 'growth_strategy_visual_wait'):
            getattr(self.features_extractor, name).requires_grad_(True)


class CityWaitBanditPolicy(CityWaitChoicePolicy):
    """Zero baseline for one-decision practice; retain the city critic intact.

    Training must use gamma=0 and vf_coef=0. Export to CityWaitChoicePolicy
    before native value-based training; the saved city critic is unchanged.
    """
    bandit_zero_baseline = True

    def forward(self, obs, deterministic=False, action_masks=None):
        actions, values, log_prob = super().forward(obs, deterministic, action_masks)
        return actions, torch.zeros_like(values), log_prob

    def evaluate_actions(self, obs, actions, action_masks=None):
        values, log_prob, entropy = super().evaluate_actions(obs, actions, action_masks)
        return torch.zeros_like(values), log_prob, entropy

    def predict_values(self, obs):
        return torch.zeros_like(super().predict_values(obs))
