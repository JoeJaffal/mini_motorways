"""Train spatial city choices while retaining the protected opening actor."""

from city_growth_policy import CityGrowthPolicy


class CityLearningPolicy(CityGrowthPolicy):
    """Allow PPO to update the spatial growth actor and service coefficients."""

    pass
