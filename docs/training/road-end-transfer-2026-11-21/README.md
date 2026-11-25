# Learning to recognize a bypass at different positions

The user approved work on recognizing a useful bypass after the [frozen transfer check](../junction-transfer-2026-11-21/README.md). On heavy boards the previous continuation opened the bypass in 7/100 moved and 0/100 combined mirror-and-move cases greedily. The Linux training checkout is `/home/mohammadjaffal/mini_motorways` on `mohammad`, base `6bd7f71` with local changes. Existing checkpoints and run directories are preserved.

## Fixture and model changes

The [isolated native patch](gap-positions.patch) extends the earlier live-junction host with three more choices of missing edge on the same side road. The new variants keep native movement, pickups, stock and legal construction. Opening the bypass restores the same side-road path for each gap position. The actor starts at second 36, with existing traffic and one paid road unit. Native controls are replays outside PPO. On 24 boards for each new training variant and traffic level, light feeder controls averaged 14.88–14.96 trips against 11.92 for the bypass. Heavy bypass controls averaged 31.71–32.08 against 29.12–29.25 for the feeder. Heavy stopped-car means dropped from 4.16–4.21 to 0.42–0.48. [Per-layout feasibility evidence](measurements/new-position-controls.json).

The endpoint residual combines the count of existing degree-one road ends a legal edit touches with visible vehicle activity. Its 2026-11-21 initialization had no completed update, so the first current run starts from those same initialized weights. A second actor uses the same visible degree and current reachability information, local and total vehicle statistics, visible demand and clock. Its edge scorer is shared across locations. It receives no position or absolute direction inputs. The critic retains the original feature extractor. A frozen smoke check verified that reflecting three native observations and their action masks reflected the actor's action probabilities to within floating-point tolerance.

Both actors learn with Maskable PPO on native trip increments. The simulator checks every legal road edit. The actor can build any one of them or Wait. No route examples enter training. The endpoint-residual experiment uses the original, mirrored and relocated gap cases. The coordinate-independent experiment trains on four missing-edge positions, including a mirrored one. It withholds the middle gap in both directions and the original shifted-and-mirrored combination. Those are tested alongside the original junction. The runs differ in architecture and training geometry, so their scores compare practical candidates rather than isolating the contribution of a single feature.

## Replays and controls

The main frozen suite starts at native second 36 and ends at second 120 or native game-over. It advances in five-second Wait intervals. It uses seeds 87200–87299 for each traffic level and layout. The score is native trips after warm-up. Low traffic is compared with opening the feeder and heavy traffic with opening the bypass. All-Wait and alternative build outcomes are retained. The report includes every legal choice, total trips, stopped-car samples and game-over status. Each policy is run greedily and with sampling, using the same seeds. The frozen replay checks stock, native score and policy fingerprints.

The earlier continuation is rerun here because [the original transfer report](../junction-transfer-2026-11-21/README.md) did not contain the two middle-gap variants. It still picked the feeder on all mirrored moved and mirrored middle boards under heavy traffic greedily. The heavy middle gap without a mirror was served by the bypass in 68/100 greedy and 63/100 sampled replays. This separates that checkpoint's orientation weakness from its response to the particular missing-edge location. [Matched prior replay](measurements/holdout-prior-continuation.json) · [Native controls](measurements/holdout-native-controls.json).

For a policy-only replay from the repository root, choose a new output path and substitute the intended checkpoint.

```bash
.venv/bin/python training/traffic_ppo.py evaluate --exercise junction \
  --stages traffic-junction-low-live traffic-junction-high-live \
           traffic-junction-low-live-mirror-shift traffic-junction-high-live-mirror-shift \
           traffic-junction-low-live-gap4 traffic-junction-high-live-gap4 \
           traffic-junction-low-live-gap4-mirror traffic-junction-high-live-gap4-mirror \
  --dll output/training/traffic-gap-positions-host-01/build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint output/training/traffic-road-topology-rush-01/latest.zip \
  --horizon 120 --warm-seconds 36 --wait-ticks 100 --offset 9200 --count 100 --workers 8 \
  --output output/training/road-end-replay-new.json
```

The `TRAFFIC` monitor line reports stage-level mean trips during collection. The inherited monitor line labels a positive-score game as connected. The corresponding checkpoint should be compared by frozen replays for bypass and feeder counts. Saved checkpoints and compiled hosts are local.

## Stronger congestion continuation

At the 18,432-decision checkpoint, the coordinate-independent actor continued to favor the feeder in greedy mode on the development heavy boards. It averaged 29.46 heavy deliveries on the original lane and 29.88 on the mirrored fifth gap. The added native pressure control increased the first flow from six to eight homes and the demand multiplier after the surge from 4.0 to 5.2. On the two training geometries under that pressure the bypass gained 3.90–4.00 deliveries over the feeder. Stopped cars went from 5.36–5.78 to 1.12–1.14. Under light traffic the feeder still won by 3.75–3.90 trips.

A third run resumed the 30,720-decision coordinate-independent checkpoint for up to 24,576 additional decisions. It uses standard traffic on the original and third gaps and stronger pressure on the third and mirrored fifth gaps. The same stock, one-edge draw or Wait, native trip reward and PPO learner remain in use. The middle gap and its mirror stay outside training. The main frozen evaluation uses standard pressure to check transfer. [Development checkpoint replays](measurements/topology-mid.json) · [Stronger traffic controls](measurements/rush-position-controls.json) · [Fixture patch](gap-positions-rush.patch).

## Coordinate-independent checkpoint

The base run finished at 40,960 decisions. It opened the bypass on 90/100 previously missed mirrored-and-shifted heavy boards, plus 88/100 and 87/100 on the unseen middle gap in its two orientations greedily. The sampled counts were 70/100, 72/100 and 69/100. All 400 light boards received the feeder in greedy mode. Stopped cars averaged 0.74–0.90 on the three changed heavy geometries, with the native bypass controls at approximately 0.39–0.45. Native replays verified legal construction and trip scoring at original stock. [All frozen episodes](measurements/holdout-topology.json).

On 32 additional paired middle-gap snapshots the frozen model's mean bypass probability was 8.1% with the light observation and 70.5% with the heavy one. Replacing only the visible traffic channels in the light observations raised bypass probability to 53.6%. Replacing only pins and warnings raised it to 18.1%. This confirms sensitivity to vehicles on the previously unseen geometry. The paired input audit held geometry and masks constant and reproduced identical pre-surge observations. [Frozen input and native passage audit](measurements/middle-gap-cue-audit.json).

## Endpoint-residual checkpoint

The endpoint-residual run stopped at its wall budget after saving 39,936 decisions. Another 144 decisions were collected in the incomplete rollout. Its greedy policy opened the bypass on all 300 changed heavy boards, and sampled play did so on 290/300. The feeder choice on the 300 corresponding light boards fell to 173/300 greedy and 166/300 sampled. On the mirrored moved and mirrored middle cases under light traffic, mean greedy deliveries were 13.22 and 13.57 compared with 15.51 for taking the feeder. The result shows strong location transfer for finding the bypass and a remaining tendency to overuse it. [All frozen episodes](measurements/holdout-endpoint-residual.json).

## Selected checkpoint

The stronger-traffic continuation saved all 24,576 added decisions, ending at 55,296 total from its 30,720-decision parent. It used both the stronger and standard native traffic conditions in training. The evaluation below uses standard traffic throughout.

| Policy | Bypass on 300 changed heavy boards, greedy / sampled | Feeder on 400 light boards, greedy / sampled |
| --- | ---: | ---: |
| Earlier geometry continuation | 68 / 84 | 399 / 376 |
| Endpoint residual | 300 / 290 | 253 / 238 |
| Coordinate-independent base | 265 / 211 | 400 / 366 |
| Selected mixed-pressure continuation | 297 / 283 | 400 / 392 |

| Heavy-traffic layout | Selected bypass, greedy / sampled | Mean greedy deliveries | Mean greedy stopped cars |
| --- | ---: | ---: | ---: |
| Original junction | 97/100 / 93/100 | 31.89 | 0.53 |
| Previously missed shifted and mirrored gap | 100/100 / 95/100 | 31.87 | 0.39 |
| Held-out middle gap | 97/100 / 93/100 | 31.89 | 0.53 |
| Held-out middle gap mirrored | 100/100 / 95/100 | 31.87 | 0.39 |

On both mirrored heavy cohorts the policy matched the native bypass control in greedy play. The earlier continuation averaged 29.49 trips and 4.13 stopped cars on each of those cohorts. The selected policy averaged 31.87 trips and 0.39 stopped cars with the same legal stock and time window. On the original and unmirrored middle cases, the bypass control averaged 31.94 trips and 0.41 stopped cars. Three of the selected greedy replays ended early in each heavy cohort, matching the corresponding bypass control. All selected light replays survived.

An independent check used seeds 89500–89563 and two more held-out combinations, the mirrored third gap and the unmirrored fifth gap. The actor opened the bypass on 123/128 greedy and 120/128 sampled heavy boards. It chose the feeder on 128/128 greedy and 126/128 sampled light boards. Heavy greedy scores were 31.67 and 31.69 trips against 31.83 and 31.91 for the native bypass. To reproduce this check with the same host and horizon, use `--offset 11500 --count 64` and `--stages traffic-junction-low-live-gap3-mirror traffic-junction-high-live-gap3-mirror traffic-junction-low-live-gap5 traffic-junction-high-live-gap5`.

On 32 new paired middle-gap snapshots, replacing only the vehicle observations in the light case raised the final model's mean initial bypass probability from 2.08% to 83.48%. Substituting visible demand alone raised it to 12.70%. The native heavy state gave 95.65%. This checks traffic sensitivity while preserving layout and legal edits. Actual native score and queues are measured separately by the replay.

`output/training/traffic-road-topology-rush-01/latest.zip` is the selected checkpoint for this junction family. The three runs saved 105,472 added decisions and have ended. The 14 existing unit tests, Python syntax, native Release builds, patch dry-runs, observation reflection and legal road-end checks passed. Across the main and independent suites, 10,080 replays checked out against the recorded host, stock, scores, common seeds and frozen fingerprints. The fixture supplies an almost complete bypass and starts after the surge. Waiting before a surge and constructing an entire bypass on a new network remain separate tests.

[Held-out final replays](measurements/holdout-topology-rush.json) · [Independent replays](measurements/final-independent-replays.json) · [Independent controls](measurements/final-independent-controls.json) · [Final cue audit](measurements/final-middle-gap-cue-audit.json) · [All matched summaries](summary.json).
