# Growing-city starting checkpoint

The first overnight milestone selected one Maskable PPO policy on `mohammad`, based on `6bd7f71` and the local growing-city adapter. The selected local checkpoint is `output/training/city-road-start-01/city-start.zip`. All checks below used frozen weights on the RTX 2080 Ti. The checkpoint has zero city training timesteps and an empty optimizer state.

## Policy and initialization

The policy reads the published visible grid across the full 50 × 30 map and visible global state. It produces a joint masked distribution over Wait and single ordinary connections. Masking uses the native simulator's current legal edges. Stock and terrain limits apply as spawns and traffic change the board. The actor outputs individual edges itself. Native deliveries are the reward, and the adapter applies the automatic weekly road-stock award when offered.

The engineering choice was to copy six tensors from the timed triad PPO checkpoint, comprising both endpoint encoder parameters, both edge encoder parameters, and both shared edge scorer parameters. The city context layers, Wait head, critic and optimizer start fresh. City road context initially adds zero to the transferred logits. An independently trainable Wait logit starts at 50% probability when roads are available. The remaining probability is allocated among legal edges by their relative logits. Wait receives 100% when the mask contains no legal roads. This keeps initial exploration of Wait independent of the number of available road edges.

## Frozen results

| Native seed | Initialization and action choice | Score | Weekly awards | Native end |
| ---: | --- | ---: | ---: | ---: |
| 2004 | Transfer, sampled | 22 | 1 | 243.25 s |
| 2004 | Fresh, sampled | 0 | 0 | 128.55 s |
| 16005 | Transfer, sampled | 15 | 1 | 236.75 s |
| 16005 | Fresh, sampled | 0 | 0 | 136.65 s |
| 2004 | Transfer, most probable individual action | 0 | 0 | 139.55 s |
| 2004 | Transfer, sampled after a four-edge scripted opening | 18 | 1 | 205.70 s |

The sampled transferred actor built from empty boards, reached the first award at second 140 on both seeds and continued to native game-over. In the sampled seed-2004 game the city grew from 2 to 13 buildings. The seed-2004 greedy actor waited throughout. Its individual Wait action initially has half the probability, which is at least as much as any one road. The fresh actor used the same architecture and initialization seed without the copied tensors. These two seed pairs support choosing the transfer checkpoint for a larger frozen baseline. Greedy cold starts and performance on fresh seeds remain open.

For the known seed-2004 opening, the transferred conditional road choice put the omitted edge first in three of four single-gap variants and second in the fourth. The fresh scorer gave each omitted edge about 0.32% conditional probability. The checks compared 256 interior logits against the old cropped scorer at a maximum absolute difference of 0.00000191. Masked rollout and PPO action log-probabilities matched, gradients were finite for all 22 parameter tensors, and reloading the ZIP reproduced the initial masked probabilities exactly. The 14 existing construction and observation tests also passed.

[Raw verification, source checkpoint and host hashes](verification.json). Weights and the compiled native host are local artifacts in ignored output. The next milestone is to measure fresh-seed baselines before launching a score-only pilot.

## Reproduce without training

Run from the Linux training checkout. Supply a new output directory. For a new host build, follow the [native preflight](../city-road-preflight-2026-11-21/README.md) and use the Release DLL path it prints.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python /home/mohammadjaffal/mini_motorways/training/prepare_city_policy.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --parent /home/mohammadjaffal/mini_motorways/output/training/triad-score-network-01/latest.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-road-start-recheck
```
