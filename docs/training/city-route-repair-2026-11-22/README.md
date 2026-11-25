# Repairing stock timing and route completion

The user asked to continue until the failure to finish connections was fixed. Work ran on `Maskable-PPO` from the seven-hour overnight city checkpoint. This follows the [road spending audit](../city-road-spending-audit-2026-11-22/README.md) and the [failed transfer from the first limited-stock pilot](../limited-route-ppo-2026-11-22/README.md).

## What changed

The native practice generator supplies long routes with one, two, or three paid edges missing, and a separate two-gap exercise whose crossing opens after a native delay. Early lessons can start just after a gate opens so PPO experiences finishing that connection before it also has to save stock. Later lessons remove the supplied roads or start with the barrier closed. A native trip remains the score. Practice updates receive a reversible credit signal based on the gap between existing road components and available stock. With gamma 1 and terminal potential zero, the shaping terms telescope to a fixed offset for each start. There is no road tax in the city environment.

The one-pair correction is a trainable part of a single Maskable PPO policy. Its inputs include visible driveway locations and membership in already-built road components. The final approach also seeds a soft preference for a legal edge that closes geometric distance between those components. The Wait score can respond to the best such evidence among the legal edges. No future route or prescribed action is computed. The correction applies to one visible matching pair within its six-cell driveway range. The frozen base handles other observations, and test predictions once multiple qualifying parcels were visible were identical to the parent.

The first launch stopped before updates because its transfer check omitted SB3's shared extractor aliases. The first corrected pilot was redirected after preserving the 32,768 and 65,536-decision saves. Geometry alone yielded one delayed two-gap success in the first two stages. A second pilot included visibility of existing road components and opened-gate practice. It was redirected after the same two checkpoint boundaries because closed-gate completion remained sparse. The [redirected runs](redirected-attempts.json) retain their configurations, checkpoint identities and completed-episode counts. The original weights and all saved checkpoints were preserved.

## Results

The final PPO continuation completed 61,440 decisions and 3,592 practice episodes in 283 seconds. On 24 fresh cases per exercise it scored on all short and long routes and 20 delayed routes. The reconstructed pre-update policy already scored on all short and long routes and 19 delayed routes in the same comparison. Much of the gain came from the new representation and starting preferences. PPO also changed the weights on progress, heading and Wait. The enriched frozen policy retained exact masked probabilities on 24 checked city observations with more than two parcels.

Four missed delayed cases exposed two issues. Diagonal progress sometimes brought a route to the barrier one tile away from the future gate, and occasional low-probability roads consumed stock during the delay. The follow-up calibration favors alignment with the other driveway and gives Wait more weight only when the legal actions contain no geometric progress. Both changes are soft preferences. The native legal mask and action selection stay with the one policy. Three of the four inspected failures scored after calibration. The stage-one development runner originally stopped on a duplicate metadata field in the city audit. That issue was fixed before the completed comparisons.

| Fresh confirmation test | Overnight parent | PPO before calibration | Selected repair |
| --- | ---: | ---: | ---: |
| Short routes scoring | 8/32 | 32/32 | 32/32 |
| Long routes scoring | 0/32 | 32/32 | 32/32 |
| Full delayed routes scoring | 0/32 | 25/32 | 32/32 |
| Delayed two-gap routes scoring | 0/32 | 30/32 | 32/32 |
| Mean deliveries on 32 full Los Angeles cities | 81.63 | 91.63 | 99.97 |
| Full cities scoring | 26/32 | 27/32 | 27/32 |

The selected repair gained 18.34 deliveries per city on average with a paired bootstrap interval of 5.81–32.13. Mean paid units outside the observed assigned trip routes remained about 37 per full city. Whole-network overbuilding remains open. The verified result covers short, long and delayed openings, with the new head active only in the local one-pair setting. It does not test other maps or other construction tools.

The selected checkpoint is [calibrated-with-counters.zip](/home/mohammadjaffal/mini_motorways/output/training/city-route-repair-calibration-01/calibrated-with-counters.zip). Its policy tensors were checked for exact equality with the evaluated ZIP. It carries the 61,440 decision count. The calibration artifact starts with a fresh optimizer if training resumes. The original overnight weights and intermediate saves are retained. The historical 32 reserved city seeds were unused here. The new native build passed 99 simulation suites and the 14 Python tests. All 36 new partial-route witnesses delivered using native legal actions.

## Reproduce the progress-conditioned pilot

From the Linux training checkout, build the current Release simulator into a fresh artifacts directory and supply that DLL path. This command performs PPO updates.

```bash
cd /home/mohammadjaffal/mini_motorways
route_build=$(mktemp -d /home/mohammadjaffal/mini_motorways/output/city-route-repair-recheck.XXXXXX)
dotnet build /home/mohammadjaffal/mini_motorways/simulation/Headless/TrafficHost.csproj \
  -c Release --nologo --artifacts-path "$route_build"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/train_city_route_repair.py \
  --dll "$route_build/bin/TrafficHost/release/TrafficHost.dll" \
  --parent /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-route-progress-recheck \
  --frontier --progress --seed-start 86600000 --rollouts 5
```

To package the calibrated policy from the trained continuation, use the same Release host and the recorded level-three checkpoint.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python /home/mohammadjaffal/mini_motorways/training/calibrate_city_route_repair.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-route-frontier-build.EK4eG9/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-route-progress-01/route-level-3.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-route-progress-recheck/calibrated.zip
```

[Confirmation summary](confirmation-summary.json) · [Confirmation games](confirmation-games.jsonl) · [Confirmation seeds](confirmation-suite.json) · [Development summary](development-summary.json) · [Training episodes by stage](training-summary.json) · [Selected checkpoint identity](selected-checkpoint.json) · [Checksums](manifest.json).
