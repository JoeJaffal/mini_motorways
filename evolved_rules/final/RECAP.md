# Evolved Rules: how the model turned out

Recap of Phase 2 (2026-10-30 to 2026-11-07). The run-by-run detail is in [`../EXPERIMENTS.md`](../EXPERIMENTS.md), and the full result tables are in [`README.md`](README.md).

## The model in one paragraph

A hand-built planner reads the map, uses A* to list candidate moves (roads from houses to shops, upgrades, waiting) and executes the one it picks. The **decision rules** that score those candidates were evolved by genetic programming (DEAP). The final model is the planner plus one evolved rule set of **24 nodes** (`gp3_final.txt`, `209634e8`):

```
priority: add(sub(neg(shop_demand), add(sub(path_cost_s, shop_demand), sub(path_cost_s, bridge_stock))), mul(15.625, is_separated))
hold:     sub(worst_margin, shops)
upgrade:  sub(sub(unserved_shops, amount), neg(unserved_houses))
remove:   -1.0
```

In plain words:
- **Priority:** prefer short, fast routes to shops that have demand, keep bridges in stock, and give a large bonus to routes that keep colours separated.
- **Hold:** wait while the worst shop still has slack.
- **Upgrade:** take offers that help reach unserved houses and shops.
- **Remove:** never remove a road.

## Headline results

All scores are mean trips on Los Angeles with a 3600 s cap, 100 maps each, and every comparison is paired by map. Each set of maps was played once, after the rules were locked.

| Comparison | Maps | GP final | Other | Difference (95% CI) | Verdict |
|---|---|---|---|---|---|
| vs hand rule | 7000–7099 | 245.9 | 170.8 | **+75.1** (+54.8, +95.5) | GP better |
| vs separated rule | 7000–7099 | 245.9 | 216.3 | **+29.6** (+9.9, +49.5) | GP better |
| vs CMA-ES weights | 7000–7099 | 245.9 | 250.6 | −4.7 (−22.9, +13.1) | tie |
| vs PPO, deterministic | 9000–9099 | 245.3 | 193.4 | **+51.9** (+31.7, +73.3) | GP better |
| vs PPO, sampled | 9000–9099 | 245.3 | 200.7 | **+44.6** (+24.9, +64.1) | GP better |

- **GP clearly beats PPO**, the two hand-written rules and the do-nothing baseline (0 trips).
- **GP ties CMA-ES.** CMA-ES only tunes the weights of a fixed linear rule (81 weights over 3 trees), and it does as well. The PLAN.md success criterion was to beat both the hand rule and CMA-ES, so it is **half met**.
- **Efficiency is about the same for every rule**, 2.6–2.8 trips per road tile. GP builds more road than CMA-ES and ends its games with 24 tiles left on average; CMA-ES ends with 48. GP's extra trips come from using the whole tile supply, not from using it better.

## How it got there

"Best" is the best rule set's score on the 50 validation maps (1500–1549). "Average" is the mean over all 64 rule sets on each generation's training maps; it moves with how hard those maps are.

| Run | Generations | Best on validation | Average, all 64 rule sets | What it taught us |
|---|---|---|---|---|
| Hand rule (phase 1) | – | 153.1 | – | the planner alone already works |
| Separated rule | – | 187.5 | – | the strongest hand-written rule |
| gp-1 | 6, paused | 222.0 | 94 → 190–305 (wild swings) | selection on 4 maps is mostly luck |
| gp-2 | 16, paused | 245.1 | 101 → about 170–200 | more maps per rule and a strict stop rule fixed the search |
| gp-3.1 / gp-3.2 | 1 / 8, stopped | 245.1 (kept from gp-2) | 92 → about 175–205 | new traffic moves; the search drifted as the best rule was lost to noise |
| gp-3.3 (hall of fame) | 12, paused | 245.1 on validation; leaders about +15 to +20 on fresh maps | 88 → about 165–218 | small rules beat gp-2's rule on fresh maps, but not on the validation maps |
| CMA-ES (control) | 30, converged | 231.8 | 238 (gen 29, its 16 candidates) | weight tuning reaches the same level |

**The key discovery: the validation maps were biased.** gp-2's rule was chosen as the best of about 43 rule sets on exactly those 50 maps, so it looked better there than it is. On 100 never-used maps it scored 240, and the small gp-3.3 rules beat it by about 15. So the final rule was not picked on validation. The four best gp-3.3 rules and gp-2's rule each played **200 unused maps (4000–4199)**, and the best mean won: 257.2, against gp-2's rule at 238.5. CMA-ES's final weights were picked the same way, for a fair comparison.

## Why games end (autopsy, 20 non-test maps, 3000–3019)

- **Cause:** car shortage 13, slow arrival 5, unreachable cars 2. None ran out of tiles.
- **At failure:** the failing colour has about 11 houses, almost all connected, and 22 cars, of which 22 are busy and almost none at home. About a third of them are stuck in traffic.
- **About 23 road tiles are still unused.**
- **The remove tree never fires**, so evolution chose not to use removals.

The limit is **traffic near shops**, not road supply or connectivity. The rule cannot buy its way out of congestion with the moves the planner offers.

## What this means

1. **The planner carries most of the performance.** GP and CMA-ES choose among the same candidates and reach the same level. PPO also gets candidates from a router, but chooses less well.
2. **Evolution found a much simpler rule.** 24 nodes against gp-2's 62 and CMA-ES's 81 weights, and it is readable.
3. **The next gains need new moves, not more search.** For example traffic lights, roundabouts or bypasses. These were left out on purpose in this phase.

## Limits to state in the report

- **Each method was run once.** There is no run-to-run variance, so these results compare these rules, not GP against CMA-ES as methods.
- **Los Angeles only.** Other cities were not tested.
- **PPO is one checkpoint** (`validation-best.zip`, about 100k steps), played with Mohammad's own evaluator. Our replays were verified (100/100); his evaluator does not verify replays. Both simulator builds play identical games (checked 9/9).
- **Choosing the best of five** on 4000–4199 flatters the winner slightly. That is why the test numbers above are the ones to report, not 257.2.

## Files in this folder

| File | What it is |
|---|---|
| `gp3_final.txt` | the final GP rule |
| `cma_final.txt` | the final CMA-ES weights |
| `selection_4000-4199.json`, `cma_selection_4000-4199.json` | how each final was chosen |
| `test_7000-7099.json` | the one-time test |
| `h2h_ppo_9000-9099.json` | the head-to-head with PPO |
| `README.md` | every table in full |
| `RECAP.md` | this summary |
