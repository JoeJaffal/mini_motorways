"""Single-city seed splits, with legacy city-split helpers for historical tools."""

from __future__ import annotations

from statistics import mean
import random


SINGLE_CITY_PROTOCOL = "single-city-seeds-v1"
DEFAULT_CITY = "LosAngeles"
DEFAULT_VALIDATION_SEED = 200_000
DEFAULT_TEST_SEED = 300_000
MAX_GAME_SEED = 2**31 - 1


class SingleCitySeeds:
    """Independent reproducible seed sampling without training/held-out overlap."""
    def __init__(self, city=DEFAULT_CITY, validation_seed=DEFAULT_VALIDATION_SEED,
                 test_seed=DEFAULT_TEST_SEED, sequence_seed=1000):
        if city not in ("LosAngeles", "Beijing", "Tokyo", "DarEsSalaam", "London"):
            raise ValueError("Unknown experiment city")
        for seed in (validation_seed,test_seed):
            if not isinstance(seed,int) or isinstance(seed,bool) or not 1<=seed<=MAX_GAME_SEED:
                raise ValueError("Held-out seeds must be positive signed 32-bit integers")
        if validation_seed==test_seed:
            raise ValueError("Validation and test seeds must be different")
        self.city=city
        self.validation_seed=validation_seed
        self.test_seed=test_seed
        self.rng=random.Random(sequence_seed)
        self.used=set()

    def training_case(self):
        while True:
            seed=self.rng.randint(1,MAX_GAME_SEED)
            if seed not in self.used and seed not in (self.validation_seed,self.test_seed):
                self.used.add(seed)
                return self.city,seed

    def validation_case(self):
        return self.city,self.validation_seed

    def test_case(self):
        return self.city,self.test_seed

    def state_dict(self):
        return {"city":self.city,"validationSeed":self.validation_seed,"testSeed":self.test_seed,
                "rngState":self.rng.getstate(),"usedSeeds":sorted(self.used)}

    def load_state_dict(self,state):
        if (state["city"],state["validationSeed"],state["testSeed"]) != (
                self.city,self.validation_seed,self.test_seed):
            raise ValueError("Seed sampler split differs from the checkpoint")
        used=state["usedSeeds"]
        if (len(set(used))!=len(used) or any(not 1<=seed<=MAX_GAME_SEED for seed in used)
                or self.validation_seed in used or self.test_seed in used):
            raise ValueError("Checkpoint training seeds overlap or are invalid")
        self.used=set(used)
        self.rng.setstate(state["rngState"])


def evaluation_cases(config, split, count=None):
    """Use a checkpoint's split; old artifacts retain their original city protocol."""
    if split not in ("validation","test"):
        raise ValueError("Unknown evaluation split")
    if config.get("experimentProtocol")==SINGLE_CITY_PROTOCOL:
        if count not in (None,1):
            raise ValueError("Single-city experiments have exactly one validation seed and one test seed")
        seeds=SingleCitySeeds(config["city"],config["validationSeed"],config["testSeed"])
        return [seeds.validation_case() if split=="validation" else seeds.test_case()]
    return validation_cases(count or 2) if split=="validation" else test_cases(count or 2)


TRAIN_CITIES = ("LosAngeles", "Beijing", "Tokyo")
VALIDATION_CITY = "DarEsSalaam"
TEST_CITY = "London"
TRAIN_SEED_BASE = 100_000
VALIDATION_SEED_BASE = 200_000
TEST_SEED_BASE = 300_000
SEED_BLOCK = 100_000


def check_counts(episodes: int, validation_seeds: int, test_seeds: int) -> None:
    if not (1 <= episodes <= SEED_BLOCK and 1 <= validation_seeds <= SEED_BLOCK
            and 1 <= test_seeds <= SEED_BLOCK):
        raise ValueError(f"Each count must be 1..{SEED_BLOCK}")


def training_case(episode: int) -> tuple[str, int]:
    if not 0 <= episode < SEED_BLOCK:
        raise ValueError("Training episode index outside reserved seed block")
    return TRAIN_CITIES[episode % len(TRAIN_CITIES)], TRAIN_SEED_BASE + episode


def validation_cases(count: int) -> list[tuple[str, int]]:
    check_counts(1, count, 1)
    return [(VALIDATION_CITY, VALIDATION_SEED_BASE + i) for i in range(count)]


def test_cases(count: int) -> list[tuple[str, int]]:
    check_counts(1, 1, count)
    return [(TEST_CITY, TEST_SEED_BASE + i) for i in range(count)]


def aggregate_rank(results: list[dict]) -> tuple[float, float, float]:
    """Completed trips first, then accumulated waiting and actual modification cost."""
    if not results:
        raise ValueError("At least one result is required")
    return (float(mean(r["trips"] for r in results)),
            -mean(r["waitingSeconds"] for r in results),
            -mean(r["modificationCost"] for r in results))
