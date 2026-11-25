# Shared local edge policy

On 19 November 2026 the user approved implementing the shared scorer and starting its pilot. The [same-layout continuation](../one-gap-single-build-continuation-2026-11-19/README.md#what-is-missing) had plateaued at 50/100, solving every vertical gap and no horizontal gap. Its first choice stayed identical across all board-observation swaps with the target legal mask fixed.

The opt-in `--policy shared-edge` option runs on the existing `one-gap-single-build` stage. It preserves layouts, one road unit, one decision, binary connectivity reward and the native legal mask. The actor scores each candidate from visible properties at its endpoints and their first ring of neighboring tiles. Each endpoint's road and driveway bits are expressed relative to the edge. The same weights score every position and direction, and combining the endpoint features symmetrically handles an edge whose canonical direction reverses under a board rotation. The value head pools edge features across the board. No coordinates, path suggestions, target edge or connectivity reward calculation enter the scorer. The narrower view is appropriate for diagnosing local repair and may need expansion for longer routes.

Fresh weights are required for the new architecture. The experiment changes the scorer and critic representation together, so it tests the new policy as a package. The previous 50/100 policy is a frozen reference. Its checkpoints remain intact and `output/training/pre-edge-policy-source.2mYVbj/source.tar` preserves the exact source matching all 17 unique saved hashes for strict resume and historical reproduction.

Ten tests passed. A translated input produced the same edge scores and a 90-degree rotation mapped scores to the corresponding rotated edges. Native mask, binary reward, separate episode credit and frozen comparison regression checks passed. A four-worker 128-attempt CUDA dry run computed losses with unchanged weights and zero updates.

## Pilot started

The fresh CUDA16 pilot is capped at 131,072 attempts or 30 minutes, matching the previous continuation's budget. The first rollout produced 2/2,048 correct builds from the initial weights, then completed four optimizer steps. Both checkpoints are present. The run was active at first-update verification. Follow `output/training/shared-edge-pilot-01-launch/training.log`. The next frozen assessment should report both orientations and repeat the board-swap check while holding the legal mask fixed. [Saved configuration](pilot-config.json), [verification and launch](verification-and-launch.json).

### Early training check

The first four completed rollouts found 2, 5, 8 and 3 repairs per 2,048 attempts, matching the first four of the earlier fresh whole-board pilot using the same seed. Roughly 460 legal choices make about four or five picks of the exact gap per rollout plausible under near-uniform sampling. The shared-edge architecture starts fresh, so comparing these early rollouts with the trained 50% checkpoint would conflate training progress and model design. No held-out result yet, and no runtime change was made.
