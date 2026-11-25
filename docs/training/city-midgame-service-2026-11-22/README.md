# Native-score midgame service pilot

The user approved a focused new-destination exercise after the [one-hour growing-city run](../city-growth-pilot-results-2026-11-22/README.md). This pilot starts from the [repaired opening checkpoint](../city-route-repair-2026-11-22/README.md) on `Maskable-PPO`. The existing opening actor is frozen. A zero-initialized later-city correction learns legal road and Wait choices with native deliveries as the only reward.

## Exercise and training

The native fixture first delivers to an established destination on a working network. It then reveals a second-color destination and a matching home attached to that network. One or two paid edges can connect the new target to the network. Stock is enough for that route with zero or one spare unit. The delayed variant blocks the target's approach tile until second 6, 9 or 12 after arrival. This is a controlled stand-in for a connection that becomes feasible after growth. The episode continues for up to 60 simulated seconds after arrival so both destinations can keep receiving deliveries.

The policy uses the existing visible board and native legal-edge mask. Per-destination delivery counts are simulator diagnostics for scoring the experiment. The policy observation schema is unchanged. Feasibility actions were used only in the fixture preflight.

The first stage uses 32 workers on immediate layouts, then the second mixes 16 immediate and 16 delayed fixtures. It is capped at 65,536 decisions with saves halfway and at the end. The initial build failed because the simulator's delivery counter is a double. The corrected Release host exposes the matching type, and training started only after the 16 scoring witnesses passed. The failed attempt made zero updates and remains in local output.

The comparison uses 24 fresh immediate layouts, 24 fresh delayed layouts, and 20 fresh full Los Angeles cities. It checks the new destination's native first delivery, stock used to get there, continued deliveries to the established destination, and full-city score and paid road use. Each checkpoint receives the same scenario and action seed. The probe for unused construction counts paid edges absent from all observed assigned trip routes.

## Timing follow-up

An independent eight-city diagnostic allowed only Wait before the visible gate opened, then returned full control to the original policy. The original policy served 0/8 normally and 8/8 with the timing control. This isolates early spending as the immediate issue on those layouts. The timing control was diagnostic only.

The targeted PPO follow-up adds a single trainable Wait weight. It starts with a soft positive bias when a matching unconnected destination has a visibly blocked driveway, all pending matching driveways are blocked, and a matching destination already has a connection. It uses the published visible board and the original native mask. The rest of the road and Wait policy is frozen. PPO updates that weight and the critic on 16,384 delayed-scenario decisions using only native delivery reward. The archived evaluation includes the seeded timing policy before updates so any benefit from the engineering prior is visible.

## Results

The initial run added 65,536 decisions in 266.37 seconds and completed 1,024 games. It delivered to the new destination on 768/768 immediate training cases and 7/256 delayed ones. The timing follow-up added 16,384 decisions in 66.49 seconds and served 255/256 delayed training cases.

| Paired review | Repaired start | Immediate-stage save | Mixed-stage save | Timing before PPO | Timing after PPO |
| --- | ---: | ---: | ---: | ---: | ---: |
| Immediately accessible targets served | 24/24 | 24/24 | 24/24 | 24/24 | 24/24 |
| Delayed targets served | 1/24 | 1/24 | 0/24 | 24/24 | 24/24 |
| Delayed cases with road stock at opening | 1/24 | 1/24 | 0/24 | 24/24 | 24/24 |
| Existing deliveries per delayed case | 3.375 | 3.375 | 3.375 | 3.375 | 3.375 |
| Full-city mean deliveries | 56.85 | 64.40 | 72.55 | 56.85 | 56.85 |
| Full cities that scored | 17/20 | 14/20 | 15/20 | 17/20 | 17/20 |

The final timing policy delivered to the new target a median 21 seconds after arrival, using 1.83 paid road units on average. New-target deliveries rose by 3.375 per delayed game, with a 95% paired bootstrap interval of 2.96–3.75. Every recorded full-city metric matched the repaired parent seed by seed for both timing checkpoints. Both averaged 36.75 paid road units outside observed routes in that full-city suite.

The controlled improvement came from the visible-blocker condition and its seeded Wait bias. PPO changed the Wait coefficient from 8 to 8.00003 and did not change sampled outcomes on this suite. The ordinary mixed checkpoint improved mean full-city score on the 20 cities but scored on fewer of them, missed the delayed exercise, and had a mean gain interval of −4.85 to +35.25. Preserve it for comparison. The [timing checkpoint](/home/mohammadjaffal/mini_motorways/output/training/city-midgame-timing-01/timing.zip) is the selected controlled midgame candidate. Use the repaired opening policy as the full-city reference until practical gains show up in growing cities. The 99 native suites and the 14 existing Python tests passed. The older reserved suite stayed unused.

## Reproduce

Use a fresh Release artifacts directory and a fresh run output path.

```bash
cd /home/mohammadjaffal/mini_motorways
midgame_build=$(mktemp -d /home/mohammadjaffal/mini_motorways/output/midgame-service-recheck.XXXXXX)
dotnet build /home/mohammadjaffal/mini_motorways/simulation/Headless/TrafficHost.csproj \
  -c Release --nologo --artifacts-path "$midgame_build"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/train_midgame_service.py \
  --dll "$midgame_build/bin/TrafficHost/release/TrafficHost.dll" \
  --parent /home/mohammadjaffal/mini_motorways/output/training/city-route-repair-calibration-01/calibrated-with-counters.zip \
  --output /home/mohammadjaffal/mini_motorways/output/city-midgame-service-recheck
```

For a frozen comparison of the saved local checkpoints, use the original pilot host.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/evaluate_midgame_service.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-midgame-service-build.hSMk1r/bin/TrafficHost/release/TrafficHost.dll \
  --city-dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoints /home/mohammadjaffal/mini_motorways/output/training/city-route-repair-calibration-01/calibrated-with-counters.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-midgame-service-02/immediate.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-midgame-service-02/mixed-delay.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-midgame-timing-01/timing-initial.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-midgame-timing-01/timing.zip \
  --output /home/mohammadjaffal/mini_motorways/output/city-midgame-review-recheck
```

[Fixture evidence](fixture-verification.json) · [Training setup](config.json) · [Saved model identities](status.json) · [Evaluation seeds](evaluation-suite.json) · [Per-game results](evaluation-games.jsonl) · [Paired summary](evaluation-summary.json) · [Checksums](manifest.json). Model ZIPs and compiled hosts are local artifacts.

Run the timing-only follow-up on the same Release host by appending `--timing --rollouts-per-stage 4` to the training command and choosing a new output directory. The timing trainer saves its initialization and its trained checkpoint.

[Wait diagnostic](timing-control.json) · [Timing setup](timing-config.json) · [Timing saves](timing-status.json) · [Training and tensor checks](training-checks.json).
