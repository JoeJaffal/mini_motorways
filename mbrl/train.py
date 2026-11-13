"""Traffic episode collection and the controlled AlphaZero training entry point."""
from __future__ import annotations

import json
import random
import time
import numpy as np

from actions import candidate_matrix, candidates, reachable_pairs, clear_caches
from environment import TrafficEnv, ReplayBranch, SnapshotBranch, material_use, visible_grid, visible_scalar
from proposals import ActionGuard, Cooldowns, proposals


def choose(visits, valid, rng, explore):
    indices = np.flatnonzero(valid)
    if not explore:
        return int(max(indices, key=lambda i: (visits[i], -i)))
    weights = visits[indices].astype(np.float64)
    return int(rng.choices(indices.tolist(), weights=weights.tolist())[0]) if weights.sum() else int(rng.choice(indices))


def outcome_rank(result):
    return result["trips"], -result["waitingSeconds"], -result["modificationCost"]


def run_episode(env: TrafficEnv, branch: ReplayBranch | SnapshotBranch, scenario: str, seed: int,
                model, simulations: int, rng: random.Random, explore: bool,
                baseline: bool = False, collect_samples: bool = True, depth: int = 4,
                safety: bool = True, cooldowns: Cooldowns = Cooldowns(),
                discount: float = .999, progress_every: int = 100, observer=None):
    from alphazero import Sample, finish_episode, predict, search
    observation = env.reset(scenario, seed)
    if observer is not None:
        observer("reset", observation, scenario=scenario, seed=seed,
                 weights={"alpha":env.alpha, "lambdaCost":env.lam, "betaCongestion":env.beta,
                          "failurePenalty":env.failure_penalty,"unansweredPenalty":env.unanswered_penalty,
                          "overcrowdingPenalty":env.overcrowding_penalty,"tripReward":env.trip_reward,
                          "clearTripBonus":env.clear_trip_bonus,"congestionFractionPenalty":env.congestion_fraction_penalty,
                          "congestionWaitThreshold":env.congestion_wait_threshold},
                 mode="heuristic" if baseline else "MCTS" if simulations else "policy")
    clear_caches()
    use_search = not baseline and simulations > 0
    if use_search:
        branch.start(observation)
    started = time.perf_counter()
    tracker = ActionGuard(cooldowns)
    samples, actions, history, predictions = [], [], [], []
    totals = {"waitingSeconds":0.0, "modificationCost":0.0, "spendingDelta":0.0, "congestionSeconds":0.0,
              "failure":0.0,"unansweredRequestSeconds":0.0,"capacityPressureSeconds":0.0,
              "clearTripUnits":0.0,"congestionFractionSeconds":0.0}
    invalid = 0
    depths = 0
    root_coverage = 0
    stopped_share = 0.0
    search_overrides = 0
    while not env.done:
        if use_search:
            available, visits, stats = search(model, env, branch, history, simulations, depth, rng,
                discount=discount, guard=tracker if safety else None, root_noise=.15 if explore else 0.0,
                observer=observer)
            value = stats["rootValue"]
            depths += stats["maxDepthReached"]
            root_coverage += stats["rootActionsVisited"]
        else:
            available = proposals(observation, env.host, tracker) if safety else candidates(observation)
            value, priors = predict(model, observation, available) if model is not None else (0, None)
            visits = priors
            stats = {"maxDepthReached":0, "rootActionsVisited":0}
        options, mask = candidate_matrix(available)
        policy_weights = np.asarray(stats.get("rootPolicy", visits), dtype=np.float64) if use_search else visits
        if baseline:
            selected = max(range(len(available)), key=lambda i:(available[i].priority, -i))
            visits = np.zeros(len(available), dtype=np.float32)
            visits[selected] = 1
            policy_weights = visits
        else:
            selected = choose(policy_weights, mask, rng, explore)
        if use_search:
            search_overrides += selected != stats["policyBest"]
        action = available[selected]
        before = observation
        outcome = env.step(action.request)
        tracker.record(before, outcome.observation, action.request, outcome.accepted)
        if use_search:
            branch.commit(action.request, outcome.observation)
        invalid += not outcome.accepted
        for name in totals:
            totals[name] += outcome.components[name]
        active = [v for v in outcome.observation["vehicles"] if v["stage"] not in ("Home", "Parking")]
        stopped_share += sum(v["waiting"] > 0 for v in active) / max(1,len(active))
        if collect_samples:
            policy = np.zeros(len(mask), dtype=np.float32)
            policy[:len(policy_weights)] = policy_weights / max(1e-12, policy_weights.sum())
            samples.append(Sample(visible_grid(before).astype(np.float16), visible_scalar(before).astype(np.float16),
                                  options.astype(np.float16), mask, policy, outcome.reward))
        predictions.append(float(value))
        actions.append({**action.request, "ticks":env.ticks_per_decision, "accepted":outcome.accepted,
            "afterTrips":outcome.observation["tripsCompleted"],
            "afterTripsDispatched":outcome.observation["tripsDispatched"],
            "afterInventory":outcome.observation["inventory"],
            "afterReachablePairs":reachable_pairs(outcome.observation),
            "afterTime":outcome.observation["time"], "reward":outcome.reward,
            "components":outcome.components, "valuePrediction":float(value), "search":stats,
            "reversals":tracker.reversals+tracker.motorway_reversals})
        if observer is not None:
            weights = policy_weights / max(1e-12, float(policy_weights.sum()))
            decision = {**actions[-1], "label":action.label, "selected":selected,
                "candidates":[{"label":item.label, "action":item.request, "weight":float(weights[i]),
                               "selected":i==selected} for i,item in enumerate(available)],
                "weightMeaning":"heuristic choice" if baseline else "search policy after comparison visits" if use_search else "policy probability"}
            observer("main", outcome.observation, decision=decision)
        history.append(action.request)
        observation = outcome.observation
        if progress_every and len(actions) % progress_every == 0:
            print(json.dumps({"phase":"progress", "map":scenario, "seed":seed,
                "time":observation["time"], "trips":observation["tripsCompleted"],
                "decisions":len(actions), "wallSeconds":time.perf_counter()-started,
                "rootActionsVisited":stats["rootActionsVisited"],
                "rootComparisonActions":stats.get("rootComparisonActions",0),
                "rootComparisonActionsVisited":stats.get("rootComparisonActionsVisited",0)}),flush=True)
    bootstrap = (predict(model, observation, candidates(observation))[0]
                 if not observation["failed"] and model is not None else 0.0)
    if samples:
        finish_episode(samples, discount, bootstrap)
    returns = []
    future = bootstrap
    for action in reversed(actions):
        future = action["reward"] + discount * future
        returns.append(future)
    targets = np.asarray(returns[::-1], dtype=np.float64)
    errors = np.asarray(predictions) - targets
    final = {"map":scenario, "seed":seed, "time":observation["time"],
        "trips":observation["tripsCompleted"], "tripsDispatched":observation["tripsDispatched"],
        "meanWaiting":observation["meanWaiting"], "materialsUsed":material_use(observation),
        "reachablePairs":reachable_pairs(observation), "invalidActions":int(invalid),
        "reversals":tracker.reversals+tracker.motorway_reversals,
        "drivewayReversals":tracker.reversals,"motorwayReversals":tracker.motorway_reversals,
        "drivewayChanges":tracker.driveway_changes,
        "motorwayChanges":tracker.motorway_changes,
        "completionRate":observation["tripsCompleted"]/max(1,observation["tripsDispatched"]),
        "congestion":stopped_share/max(1,len(actions)), "wallSeconds":time.perf_counter()-started,
        "meanSearchDepthReached":depths/max(1,len(actions)),
        "meanRootActionsVisited":root_coverage/max(1,len(actions)),
        "searchOverrides":int(search_overrides), "searchOverrideRate":search_overrides/max(1,len(actions)),
        "valueRMSE":float(np.sqrt(np.mean(errors**2))), "valueBias":float(np.mean(errors)),
        "valueExplainedVariance":float(1-np.var(errors)/max(1e-9,np.var(targets))),
        "terminated":bool(observation["failed"]), "truncated":not observation["failed"],
        "meanBlockedFraction":totals["congestionFractionSeconds"]/max(1e-12,observation["time"]),
        "decisions":len(actions), **totals}
    recording = {"schemaVersion":1, "seed":seed, "score":final["trips"], "policySteps":len(actions),
        "episode":0, "version":"OriginalReference", "scenario":scenario, "variation":"SameMap",
        "duration":final["time"], "terminated":final["terminated"], "truncated":final["truncated"],
        "source":"mbrl/train.py", "policySchema":"guarded-candidates-v2", "actions":actions,
        "rewardWeights":{"alpha":env.alpha,"lambdaCost":env.lam,"betaCongestion":env.beta,
                         "failurePenalty":env.failure_penalty,"unansweredPenalty":env.unanswered_penalty,
                         "overcrowdingPenalty":env.overcrowding_penalty,"tripReward":env.trip_reward,
                         "clearTripBonus":env.clear_trip_bonus,"congestionFractionPenalty":env.congestion_fraction_penalty,
                         "congestionWaitThreshold":env.congestion_wait_threshold}}
    if observer is not None:
        observer("finish", observation, result=final)
    return samples, final, recording


if __name__ == "__main__":
    from experiment import main
    main()
