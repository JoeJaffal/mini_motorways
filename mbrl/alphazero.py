"""Simulator-search AlphaZero agent for structured traffic observations."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from actions import ACTION_WIDTH, candidate_matrix, candidates
from environment import GRID_CHANNELS, LEGACY_GRID_CHANNELS, SCALAR_FEATURES, ReplayBranch, SnapshotBranch, TrafficEnv, visible_grid, visible_scalar
from proposals import ActionGuard, key, proposals


ROOT_COMPARISON_ACTIONS = 4


class Network(nn.Module):
    def __init__(self, hidden: int = 128, value_scale: float = 10.0):
        super().__init__()
        self.value_scale = value_scale
        self.grid = nn.Sequential(nn.Conv2d(GRID_CHANNELS, 32, 5, stride=2, padding=2), nn.ReLU(),
                                  nn.Conv2d(32, 32, 3, stride=2, padding=1), nn.ReLU(),
                                  nn.Flatten(), nn.Linear(32 * 8 * 13, hidden), nn.ReLU())
        self.encoder = nn.Sequential(nn.Linear(hidden + SCALAR_FEATURES, hidden), nn.ReLU())
        self.policy = nn.Sequential(nn.Linear(hidden + ACTION_WIDTH, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        self.value = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def load_compatible_state_dict(self, state):
        """Warm-start 39-channel weights with zero influence from new risk inputs."""
        state = dict(state)
        weight = state["grid.0.weight"]
        if weight.shape[1] == LEGACY_GRID_CHANNELS and self.grid[0].in_channels == GRID_CHANNELS:
            expanded = weight.new_zeros((weight.shape[0], GRID_CHANNELS, *weight.shape[2:]))
            expanded[:, :LEGACY_GRID_CHANNELS] = weight
            state["grid.0.weight"] = expanded
        return self.load_state_dict(state)

    def forward(self, grid: torch.Tensor, scalar: torch.Tensor, actions: torch.Tensor,
                mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        state = self.encoder(torch.cat((self.grid(grid), scalar), -1))
        logits = self.policy(torch.cat((state[:, None].expand(-1, actions.shape[1], -1), actions), -1)).squeeze(-1)
        return self.value(state).squeeze(-1) * self.value_scale, logits.masked_fill(~mask, -1e9)


@torch.no_grad()
def predict(model: Network, observation: dict, items: list) -> tuple[float, np.ndarray]:
    device = next(model.parameters()).device
    options, mask = candidate_matrix(items)
    value, logits = model(
        torch.as_tensor(visible_grid(observation)[None], device=device),
        torch.as_tensor(visible_scalar(observation)[None], device=device),
        torch.as_tensor(options[None], device=device),
        torch.as_tensor(mask[None], device=device))
    return float(value.item()), F.softmax(logits[0, :len(items)], -1).cpu().numpy()


@dataclass
class Edge:
    prior: float
    visits: int = 0
    total: float = 0.0
    outcomes: list["Outcome"] = field(default_factory=list)
    in_flight: int = 0
    pending: int = 0

    @property
    def q(self) -> float:
        return self.total / self.visits if self.visits else 0.0


@dataclass
class Node:
    observation: dict
    items: list
    value: float
    edges: list[Edge]
    terminal: bool = False
    guard: ActionGuard | None = None

    @property
    def visits(self) -> int:
        return sum(e.visits for e in self.edges)


@dataclass
class Outcome:
    seed: int
    reward: float
    child: Node
    visits: int = 1


def search_value(edge: Edge, node_value: float) -> float:
    """Use the state baseline for unvisited and temporarily reserved work."""
    count = edge.visits + edge.in_flight
    return (edge.total + edge.in_flight * node_value) / count if count else node_value


def make_node(model: Network, observation: dict, terminal: bool = False,
              guard: ActionGuard | None = None, host=None, truncated: bool = False) -> Node:
    if terminal:
        return Node(observation, [], 0.0, [], True)
    items = proposals(observation, host, guard) if guard is not None and not truncated else candidates(observation)
    value, priors = predict(model, observation, items)
    if truncated:
        return Node(observation, [], value, [], True, guard)
    return Node(observation, items, value, [Edge(float(p)) for p in priors], False, guard)


def root_comparison_indices(root: Node, simulations: int) -> list[int]:
    """Wait, best alternative, then favor other command/tool families up to four."""
    limit = min(ROOT_COMPARISON_ACTIONS, simulations, len(root.items))
    if limit <= 0:
        return []
    ranked = sorted(range(len(root.items)), key=lambda i: (-root.edges[i].prior, i))
    selected, identities, families = [], set(), set()

    def family(index):
        request = root.items[index].request
        return request["command"], request.get("tool", "")

    def add(index):
        identity = key(root.items[index].request)
        if len(selected) < limit and identity not in identities:
            selected.append(index)
            identities.add(identity)
            families.add(family(index))

    wait = next((i for i in ranked if root.items[i].request["command"] == "wait"), None)
    if wait is not None:
        add(wait)
    best = next((i for i in ranked if root.items[i].request["command"] != "wait"), None)
    if best is not None:
        add(best)
    for index in ranked:
        if family(index) not in families:
            add(index)
    # If few families are available, compare other distinct requests in prior order.
    for index in ranked:
        add(index)
    return selected


def root_policy(visits, compared: list[int], priors) -> tuple[np.ndarray, np.ndarray, str]:
    """Mandatory inspection is not policy support; keep only subsequent visits."""
    visits = np.asarray(visits, dtype=np.float64)
    support = visits.copy()
    for index in compared:
        support[index] = max(0.0, support[index] - 1)
    if support.sum() > 0:
        return support / support.sum(), support, "postComparisonVisits"
    # Tiny budgets can end after the opening probes. Do not invent an equal
    # preference from those probes; retain policy priors among inspected actions.
    weights = np.where(visits > 0, priors, 0.0).astype(np.float64)
    if weights.sum() <= 0:
        weights = (visits > 0).astype(np.float64)
    total = weights.sum()
    return weights / total if total else weights, support, "priorFallback"


def root_comparison_stats(root: Node, compared: list[int], policy_priors) -> dict:
    selected = set(compared)
    policy, support, mode = root_policy([e.visits for e in root.edges], compared, policy_priors)
    return {"rootComparisonActions": len(compared),
            "rootComparisonActionsVisited": sum(root.edges[i].visits > 0 for i in compared),
            "rootPolicy": policy.tolist(), "rootPolicySource": mode,
            "rootActionStats": [
                {"index": i, "action": root.items[i].request, "prior": edge.prior,
                 "policyPrior": float(policy_priors[i]), "visits": edge.visits,
                 "searchSupportVisits": int(support[i]), "policyWeight": float(policy[i]),
                 "meanReturn": edge.q, "initialComparison": i in selected}
                for i, edge in enumerate(root.edges) if edge.visits]}


def search(model: Network, live: TrafficEnv, branch: ReplayBranch | SnapshotBranch, history: list[dict],
           simulations: int, depth: int, rng: random.Random, discount: float = 0.997,
           exploration: float = 1.5, outcomes_per_action: int = 2,
           guard: ActionGuard | None = None, root_noise: float = 0.0,
           observer=None) -> tuple[list, np.ndarray, dict]:
    """PUCT over independently replayed Unity futures; backups use scalar single-agent returns."""
    if getattr(branch, "workers", 1) > 1:
        from parallel_search import parallel_search
        return parallel_search(model, live, branch, history, simulations, depth, rng, discount,
                               exploration, outcomes_per_action, guard, root_noise, observer)
    if live.observation is None:
        raise RuntimeError("Reset the live environment before search")
    model.eval()
    root = make_node(model, live.observation, guard=guard, host=live.host)
    policy_priors = [edge.prior for edge in root.edges]
    policy_best = int(np.argmax([edge.prior for edge in root.edges]))
    compared = root_comparison_indices(root, simulations)
    if root_noise:
        noise = np.asarray([rng.gammavariate(.3, 1) for _ in root.edges])
        noise /= noise.sum()
        for edge, extra in zip(root.edges, noise):
            edge.prior = (1-root_noise)*edge.prior + root_noise*float(extra)
    deepest = 0
    expansions = 0
    transitions = 0
    for simulation in range(simulations):
        branch.restore(history, live.observation)
        if observer is not None:
            observer("search", live.observation, simulation=simulation+1, depth=0)
        node = root
        trail: list[tuple[Edge, float]] = []
        for level in range(depth):
            if node.terminal or not node.edges:
                break
            if level == 0 and simulation < len(compared):
                index = compared[simulation]
                edge = node.edges[index]
            else:
                index, edge = max(enumerate(node.edges), key=lambda pair: (
                    search_value(pair[1], node.value) / model.value_scale + exploration * pair[1].prior * math.sqrt(node.visits + 1) / (pair[1].visits + 1),
                    -pair[0]))
            if len(edge.outcomes) < outcomes_per_action:
                expansions += 1
                seed = rng.randrange(1, 2**31)
                transition = branch.transition(node.items[index].request, seed)
                transitions += 1
                if observer is not None:
                    observer("search", transition.observation, simulation=simulation+1, depth=level+1,
                             action=node.items[index].request, reward=transition.reward,
                             components=transition.components, accepted=transition.accepted, futureSeed=seed)
                child_guard = node.guard.clone() if node.guard is not None else None
                if child_guard is not None:
                    child_guard.record(node.observation, transition.observation, node.items[index].request, transition.accepted)
                child = make_node(model, transition.observation, transition.terminated,
                                  child_guard, branch.env.host, transition.truncated)
                edge.outcomes.append(Outcome(seed, transition.reward, child))
                trail.append((edge, transition.reward))
                node = child
                deepest = max(deepest, level + 1)
                break
            outcome = min(edge.outcomes, key=lambda sampled: sampled.visits)
            outcome.visits += 1
            transition = branch.transition(node.items[index].request, outcome.seed)
            transitions += 1
            if transition.observation != outcome.child.observation:
                raise RuntimeError("Counterfactual branch replay diverged")
            if observer is not None:
                observer("search", transition.observation, simulation=simulation+1, depth=level+1,
                         action=node.items[index].request, reward=transition.reward,
                         components=transition.components, accepted=transition.accepted, futureSeed=outcome.seed)
            trail.append((edge, outcome.reward))
            node = outcome.child
            deepest = max(deepest, level + 1)
        value = node.value
        for edge, reward in reversed(trail):
            value = reward + discount * value
            edge.visits += 1
            edge.total += value
    stats = {"maxDepthReached": deepest, "expandedOutcomes": expansions,
             "rootActionsVisited": sum(edge.visits > 0 for edge in root.edges), "rootValue":root.value,
             "policyBest":policy_best,"searchWorkers":1,"peakSearchWorkers":int(simulations>0),
             "parallelWaves":simulations,"rolloutsCompleted":simulations,"simulatorTransitions":transitions}
    stats.update(root_comparison_stats(root, compared, policy_priors))
    return root.items, np.asarray([edge.visits for edge in root.edges], dtype=np.float32), stats


@dataclass
class Sample:
    grid: np.ndarray
    scalar: np.ndarray
    options: np.ndarray
    mask: np.ndarray
    policy: np.ndarray
    reward: float
    value_target: float = 0.0


class ReplayMixture:
    """Permanent demonstrations plus bounded recent and successful episode references."""
    def __init__(self, max_recent_states: int = 6000):
        self.demonstrations = []
        self.recent = []
        self.max_recent_states = max_recent_states

    def state_dict(self):
        return {"demonstrations": self.demonstrations, "recent": self.recent,
                "max_recent_states": self.max_recent_states}

    def load_state_dict(self, state):
        self.demonstrations = state["demonstrations"]
        self.recent = state["recent"]
        self.max_recent_states = state["max_recent_states"]

    def add(self, samples: list[Sample], result: dict, demonstration: bool = False):
        item = (samples, dict(result))
        if demonstration:
            self.demonstrations.append(item)
        else:
            self.recent.append(item)
            while len(self.recent) > 1 and sum(len(e[0]) for e in self.recent) > self.max_recent_states:
                self.recent.pop(0)

    def sample(self, rng: random.Random, count: int):
        successful = []
        for city in sorted({r[1]["map"] for r in self.recent}):
            group = sorted([r for r in self.recent if r[1]["map"] == city],
                           key=lambda item: item[1]["trips"], reverse=True)
            successful.extend([r for r in group[:max(1, len(group)//2)] if r[1]["trips"] > 0])
        pools = [self.demonstrations, self.recent, successful]
        weights = [.35, .40, .25]
        available = [(pool, weight) for pool, weight in zip(pools, weights) if pool]
        picked = []
        for _ in range(count):
            pool = rng.choices([p for p, _ in available], weights=[w for _, w in available])[0]
            episode, _ = rng.choice(pool)
            picked.append(rng.choice(episode))
        return picked


def finish_episode(samples: list[Sample], discount: float = 0.997,
                   bootstrap_value: float = 0.0) -> None:
    future = bootstrap_value
    for sample in reversed(samples):
        future = sample.reward + discount * future
        sample.value_target = future


def train_batch(model: Network, optimizer: torch.optim.Optimizer, episodes,
                batch_size: int = 32, rng: random.Random | None = None,
                policy_weight: float = 1.0, value_weight: float = 1.0,
                value_loss: str = "huber", return_metrics: bool = False):
    rng = rng or random.Random()
    if isinstance(episodes, ReplayMixture):
        picked = episodes.sample(rng, batch_size)
    else:
        pool = [sample for episode in episodes for sample in episode]
        if not pool:
            raise ValueError("Replay is empty")
        picked = rng.choices(pool, k=batch_size)
    device = next(model.parameters()).device
    grid = torch.as_tensor(np.stack([s.grid for s in picked]), device=device, dtype=torch.float32)
    scalar = torch.as_tensor(np.stack([s.scalar for s in picked]), device=device, dtype=torch.float32)
    # Preserve historical 24-row demonstrations when mixing with new 48-row replay.
    # Candidate slots have no fixed identity; extra rows are masked padding.
    candidate_count = max(s.options.shape[0] for s in picked)
    def padded(name):
        rows = []
        for sample in picked:
            array = getattr(sample, name)
            padding = [(0, candidate_count - array.shape[0])] + [(0, 0)] * (array.ndim - 1)
            rows.append(np.pad(array, padding))
        return np.stack(rows)
    options = torch.as_tensor(padded("options"), device=device, dtype=torch.float32)
    mask = torch.as_tensor(padded("mask"), device=device)
    policy = torch.as_tensor(padded("policy"), device=device)
    target = torch.as_tensor([s.value_target for s in picked], device=device)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    value, logits = model(grid, scalar, options, mask)
    policy_loss = -(policy * F.log_softmax(logits, -1)).sum(-1).mean()
    predicted, normalized_target = value / model.value_scale, target / model.value_scale
    value_error = (F.smooth_l1_loss(predicted, normalized_target) if value_loss == "huber"
                   else F.mse_loss(predicted, normalized_target))
    loss = policy_weight * policy_loss + value_weight * value_error
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError("Non-finite training loss")
    metrics = {}
    if return_metrics:
        shared = list(model.grid.parameters()) + list(model.encoder.parameters())
        pg = torch.autograd.grad(policy_weight * policy_loss, shared, retain_graph=True)
        vg = torch.autograd.grad(value_weight * value_error, shared, retain_graph=True)
        policy_norm = torch.sqrt(sum(g.square().sum() for g in pg))
        value_norm = torch.sqrt(sum(g.square().sum() for g in vg))
        metrics = {"policyLoss":float(policy_loss.detach()), "valueLoss":float(value_error.detach()),
                   "policyEncoderGradient":float(policy_norm), "valueEncoderGradient":float(value_norm),
                   "gradientCosine":float(sum((a*b).sum() for a,b in zip(pg,vg)) /
                                          (policy_norm*value_norm + 1e-12)),
                   "valueRMSE":float(torch.sqrt(F.mse_loss(value.detach(), target)))}
    loss.backward()
    gradient = nn.utils.clip_grad_norm_(model.parameters(), 5.0,error_if_nonfinite=True)
    optimizer.step()
    if return_metrics:
        metrics.update(loss=float(loss.detach().cpu()), totalGradient=float(gradient))
        return metrics
    return float(loss.detach().cpu())
