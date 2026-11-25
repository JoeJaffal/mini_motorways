# Limited-stock route completion with score-only PPO

The user approved a focused exercise after the [road-spending audit](../city-road-spending-audit-2026-11-22/README.md). The starting weights and Adam state come from the [seven-hour city checkpoint](../city-overnight-results-2026-11-22/README.md). The actor still sees the 50 × 30 visible observation contract and selects an ordinary native road edge or Wait. The task ends at the first native delivery, native game-over, or 55 simulated seconds. Native deliveries are the only reward.

## Exercise

The short exercise requires two or three paid edges. The long and delayed exercises require four or five, with zero or one spare unit across the fixtures. Each has one matching house and destination, varied directions and translations, and two genuine road stubs as competing choices. The delayed fixture starts with a physical barrier across the playable arena. A single passage opens after 6, 9, or 12 simulated seconds. The policy can Wait or spend its stock on currently legal edges. Fixture references are used for feasibility checks. They are excluded from the actor, action mask and reward.

The CUDA run uses 32 workers. Stage one collects 40,960 decisions on short and long routes. Stage two collects another 40,960 decisions with eight delayed workers and the remaining workers retaining the undelayed exercises. The city architecture and optimizer state carry over. Practice seeds are in `[84000000,84500000)`. Practice validation uses separate scenario seeds and a translated placement band. City retention uses 16 new Los Angeles starts with the existing city DLL and native 600-second protocol. The parent and both candidates are compared with the same action draws.

The first launch reached fixture preflight and stopped before updates because NumPy integers were passed to the JSON bridge. The retry marshals actions as ordinary Python integers and checks that accepted builds created the requested native connection. The unsuccessful first attempt remains in local output.

## Results

The successful run finished 81,920 decisions and 1,400 practice episodes in 294.12 seconds. The native headless build passed 99 simulation suites and the existing Python tests passed 14/14. In fixture checks, all 36 references delivered within stock. A separate legal-mask reachability check verified that all 12 checked delayed layouts had no possible connection just before the gate opened and had one when it opened.

| Held-out measure | Overnight parent | Undelayed stage | Mixed-delay stage |
| --- | ---: | ---: | ---: |
| Short routes scoring | 6/32 | 9/32 | 12/32 |
| Long routes scoring | 0/32 | 0/32 | 1/32 |
| Delayed routes scoring | 0/32 | 0/32 | 0/32 |
| Delayed layouts with stock at opening | 0/32 | 0/32 | 26/32 |
| Fresh-city mean deliveries | 72.13 | 66.56 | 39.69 |
| Fresh cities scoring | 13/16 | 13/16 | 13/16 |

The final checkpoint converted six short-route failures into successes and lost none of the parent's short-route successes. The gain was 18.75 percentage points, with a paired bootstrap interval of 6.25–34.38 points. Saving some stock at the barrier improved, while completing the connection after it opened remained unsolved. Fresh-city performance declined by 32.44 deliveries on average at the final save, with a paired interval of −50.75 to −15.37. Keep the seven-hour checkpoint as the full-city reference and preserve both practice saves. The original reserved suite was unused.

A smaller next step would give the agent partially completed long routes with a one- or two-edge gap, then progressively remove the supplied pieces. Apply the same progression after the gate opens. Verify that short-route and full-city performance transfer before replacing the city checkpoint.

## Reproduce

Build the current Linux headless simulator into a fresh local directory, then run the bounded task with a fresh output path.

```bash
cd /home/mohammadjaffal/mini_motorways
route_build=$(mktemp -d /home/mohammadjaffal/mini_motorways/output/city-limited-route-recheck.XXXXXX)
dotnet build /home/mohammadjaffal/mini_motorways/simulation/Headless/TrafficHost.csproj \
  -c Release --nologo --artifacts-path "$route_build"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/train_limited_route_ppo.py \
  --dll "$route_build/bin/TrafficHost/release/TrafficHost.dll" \
  --parent /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/limited-route-ppo-recheck
```

To compare the recorded checkpoints, use the exact native host from the run.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/evaluate_limited_route_ppo.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-limited-route-build.cm4Ifa/bin/TrafficHost/release/TrafficHost.dll \
  --city-dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoints /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
    /home/mohammadjaffal/mini_motorways/output/training/limited-route-ppo-02/openings.zip \
    /home/mohammadjaffal/mini_motorways/output/training/limited-route-ppo-02/mixed-delay.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/limited-route-ppo-eval-recheck
```

[Configuration](config.json) · [Checkpoint hashes](status.json) · [Fixture witnesses](fixture-verification.json) · [Evaluation summary](evaluation-summary.json) · [Per-game evaluation](evaluation-games.jsonl) · [Manifest](manifest.json). The weight ZIPs and compiled hosts remain local.
