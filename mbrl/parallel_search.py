"""Deterministic batched shared-tree search over independent simulator processes.

Only the coordinator mutates the tree or invokes viewer callbacks. Worker threads
wait on separate .NET hosts, whose simulation work runs on separate CPU cores.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import ExitStack
import math

import numpy as np

from environment import Host


def add_search_arguments(parser):
    parser.add_argument("--search-workers", type=int, default=1,
                        help="Independent simulator workers; total rollout budget is shared (default: 1)")
    parser.add_argument("--torch-threads", type=int, default=1,
                        help="PyTorch CPU computation threads, shared by all search workers (default: 1)")


def configure_search(args):
    if args.search_workers < 1 or args.torch_threads < 1:
        raise ValueError("--search-workers and --torch-threads must be positive")
    import torch
    torch.set_num_threads(args.torch_threads)


class SearchPool:
    """Own extra hosts and a persistent executor; retain the ordinary branch API."""
    def __init__(self, branch, workers=1):
        if workers < 1:
            raise ValueError("Search worker count must be positive")
        self.branches = [branch]
        self.workers = workers
        self.env = branch.env
        self.stack = ExitStack()
        self.executor = None

    def __enter__(self):
        try:
            original = self.branches[0]
            for _ in range(self.workers - 1):
                host = original.env.host
                other = self.stack.enter_context(Host(dotnet=host.dotnet, dll=host.dll, timeout=host.timeout))
                self.branches.append(type(original)(other, original.live))
            if self.workers > 1:
                # Registered last: all work finishes before hosts are closed.
                self.executor = self.stack.enter_context(ThreadPoolExecutor(max_workers=self.workers,
                                                                            thread_name_prefix="traffic-search"))
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def run(self, jobs):
        """Jobs are (callable, args). Drain every task before propagating errors."""
        if self.executor is None:
            return [fn(*args) for fn, args in jobs]
        futures = [self.executor.submit(fn, *args) for fn, args in jobs]
        try:
            return [future.result() for future in futures]
        finally:
            wait(futures)

    def start(self, expected):
        self.run([(branch.start, (expected,)) for branch in self.branches])

    def commit(self, action, expected):
        self.run([(branch.commit, (action, expected)) for branch in self.branches])

    def restore(self, history, expected):
        return self.branches[0].restore(history, expected)

    def transition(self, action, future_seed):
        return self.branches[0].transition(action, future_seed)


def parallel_search(model, live, pool, history, simulations, depth, rng, discount,
                    exploration, outcomes_per_action, guard, root_noise, observer):
    from alphazero import Outcome, make_node, root_comparison_indices, root_comparison_stats, search_value
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

    def reserve(forced_root=None):
        node, steps, trail, revisited = root, [], [], []
        expanding = None
        for level in range(depth):
            if node.terminal or not node.edges:
                break
            available = [(i, edge) for i, edge in enumerate(node.edges)
                         if edge.outcomes or edge.pending < outcomes_per_action]
            if not available:
                for edge in trail:
                    edge.in_flight -= 1
                for outcome in revisited:
                    outcome.visits -= 1
                return None
            visits = sum(edge.visits + edge.in_flight for edge in node.edges)
            if level == 0 and forced_root is not None:
                index, edge = forced_root, node.edges[forced_root]
            else:
                index, edge = max(available, key=lambda pair: (
                    search_value(pair[1], node.value) / model.value_scale
                    + exploration * pair[1].prior * math.sqrt(visits + 1)
                    / (pair[1].visits + pair[1].in_flight + 1), -pair[0]))
            edge.in_flight += 1  # Reserve work at the state's value, independent of return sign.
            trail.append(edge)
            if len(edge.outcomes) + edge.pending < outcomes_per_action:
                seed = rng.randrange(1, 2**31)
                edge.pending += 1
                steps.append((node.items[index].request, seed, None))
                expanding = edge
                break
            outcome = min(edge.outcomes, key=lambda item: item.visits)
            outcome.visits += 1
            revisited.append(outcome)
            steps.append((node.items[index].request, outcome.seed, outcome.child.observation))
            node = outcome.child
        return steps, trail, node, expanding

    def execute(branch, plan):
        steps, _, leaf, expanding = plan
        branch.restore(history, live.observation)
        rewards, events = [], []
        before = live.observation
        for action, seed, expected in steps:
            transition = branch.transition(action, seed)
            if expected is not None and transition.observation != expected:
                raise RuntimeError("Counterfactual branch replay diverged")
            rewards.append(transition.reward)
            events.append((transition.observation, action, seed, transition))
            if expected is None:
                child_guard = leaf.guard.clone() if leaf.guard is not None else None
                if child_guard is not None:
                    child_guard.record(before, transition.observation, action, transition.accepted)
                leaf = make_node(model, transition.observation, transition.terminated,
                                 child_guard, branch.env.host, transition.truncated)
            before = transition.observation
        return leaf, rewards, events

    completed = expansions = deepest = transitions = waves = peak = 0
    comparison_cursor = 0
    while completed < simulations:
        plans = []
        comparing = comparison_cursor < len(compared)
        wave_limit = len(compared)-comparison_cursor if comparing else pool.workers
        for _ in range(min(pool.workers, simulations-completed, wave_limit)):
            forced = compared[comparison_cursor] if comparing else None
            plan = reserve(forced)
            if plan is None:
                break
            plans.append(plan)
            if comparing:
                comparison_cursor += 1
        if not plans:
            raise RuntimeError("Parallel search could not reserve any work")
        results = pool.run([(execute, (pool.branches[i], plan)) for i, plan in enumerate(plans)])
        waves += 1
        peak = max(peak, len(plans))
        # Stable reservation/backup order makes results independent of completion order.
        for offset, (plan, result) in enumerate(zip(plans, results)):
            steps, trail, _, expanding = plan
            leaf, rewards, events = result
            for edge in trail:
                edge.in_flight -= 1
            if expanding is not None:
                expanding.pending -= 1
                expanding.outcomes.append(Outcome(steps[-1][1], rewards[-1], leaf))
                expansions += 1
            value = leaf.value
            for edge, reward in reversed(list(zip(trail, rewards))):
                value = reward + discount * value
                edge.visits += 1
                edge.total += value
            deepest = max(deepest, len(steps))
            transitions += len(steps)
            if observer is not None:
                observer("search", live.observation, simulation=completed+offset+1, depth=0, worker=offset+1)
                for level, (observation, action, seed, transition) in enumerate(events, 1):
                    observer("search", observation, simulation=completed+offset+1, depth=level,
                             worker=offset+1, action=action, reward=transition.reward,
                             components=transition.components, accepted=transition.accepted, futureSeed=seed)
        completed += len(plans)
    stats = {"maxDepthReached":deepest, "expandedOutcomes":expansions,
             "rootActionsVisited":sum(edge.visits > 0 for edge in root.edges),
             "rootValue":root.value, "policyBest":policy_best, "searchWorkers":pool.workers,
             "peakSearchWorkers":peak, "parallelWaves":waves,
             "rolloutsCompleted":completed, "simulatorTransitions":transitions}
    stats.update(root_comparison_stats(root, compared, policy_priors))
    return root.items, np.asarray([edge.visits for edge in root.edges], dtype=np.float32), stats
