"""Check the 48-candidate input and mixed historical/current replay batches."""
import copy
import random

import numpy as np
import torch

from actions import Candidate, MAX_CANDIDATES, _features, candidate_matrix
from alphazero import Network, ReplayMixture, Sample, train_batch
from environment import visible_grid, visible_scalar
from smoke import observation


def checks():
    torch.set_num_threads(1)
    torch.manual_seed(7)
    items = [Candidate({"command": "wait"}, str(i), _features(0)) for i in range(49)]
    options, mask = candidate_matrix(items[:48])
    assert options.shape == (48, 26) and mask.all()
    try:
        candidate_matrix(items)
    except ValueError:
        pass
    else:
        raise AssertionError("49 candidates bypassed the cap")
    obs = observation()
    grid, scalar = visible_grid(obs), visible_scalar(obs)
    model = Network(value_scale=100)
    value, logits = model(torch.from_numpy(grid[None]), torch.from_numpy(scalar[None]),
                          torch.from_numpy(options[None]), torch.from_numpy(mask[None]))
    assert value.shape == (1,) and logits.shape == (1, MAX_CANDIDATES)

    # The same two valid choices must learn identically, regardless of padding size.
    options, mask = candidate_matrix(items[:2])
    target = np.zeros(48, dtype=np.float32)
    target[:2] = [.25, .75]
    current = Sample(grid, scalar, options, mask, target, 0, 3)
    historical = Sample(grid, scalar, options[:24], mask[:24], target[:24], 0, 3)

    class FixedReplay(ReplayMixture):
        def __init__(self, samples):
            self.samples = samples

        def sample(self, rng, count):
            return self.samples

    models = [copy.deepcopy(model), copy.deepcopy(model)]
    losses = []
    for trial, samples in zip(models, ([historical, historical], [historical, current])):
        optimizer = torch.optim.SGD(trial.parameters(), lr=.001)
        losses.append(train_batch(trial, optimizer, FixedReplay(samples), batch_size=2, rng=random.Random(1)))
    assert abs(losses[0]-losses[1]) < 1e-6
    for a, b in zip(models[0].parameters(), models[1].parameters()):
        assert torch.allclose(a, b, atol=1e-7, rtol=1e-5)
    assert historical.options.shape == (24, 26) and current.options.shape == (48, 26)
    print("PASS: 48-choice forward pass, capacity enforcement, compatible weights, mixed 24/48 replay padding")


if __name__ == "__main__":
    checks()
