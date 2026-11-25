# Wait restoration review

The explicit checkpoint migration retains trained road weights and Adam history, restores original zero-output Wait corrections, and freezes them. This recovers much of the observed city regression in the probability-component diagnostic; it does not establish a gain over the original.

| Exercise | Original success | Restored success |
|---|---:|---:|
| adjacent | 16/16 | 16/16 |
| bend | 16/16 | 16/16 |
| clear | 16/16 | 16/16 |
| obstacle | 14/16 | 14/16 |
| small-city-offset-pairs | 3/16 | 5/16 |
| small-city-offset-single | 8/16 | 8/16 |
| small-city-offset-stock | 8/16 | 8/16 |

Small-city evaluation uses300seconds for both policies; the four old geometry tasks remain60seconds. Two-pair success in this table requires both destinations served. Native score only.

The restored policy fails the declared development screen: tight singles remain8/16, and both-pair service is5/16 versus a target of8/16. No promotion or overnight launch. Preserve this candidate for possible bounded road-learning work after the ongoing comparisons.

Migration checks preserve all non-Wait weights,22named Adam states at8192steps, lifetime decision and SB3 update counters.384shared states match the intended component distribution within5.35e-7. A disposable optimizer update changes roads/spatial encoder/critic while Wait stays within3.58e-7 on12shared states; the saved checkpoint and8192step optimizer remain unchanged. This checks mechanics, not training effectiveness.

Checkpoint weights are local-only at output/training/mini-reset-wait-repair-01/start.zip. Source, hashes, raw112-game results and optimizer checks accompany this report.




## Visual verification of Wait-restored mini behavior
Four exact replays completed: original/restored on the lowest-seed newly both-served pair (231000003) and lowest-seed tight failure (231000000). Every existing archived metric matches. Paired frame sheets visually inspected. In the improved pair, original spends its12 units on one served route plus disconnected fragments; restored serves both colors and survives300seconds (36deliveries vs11before original native failure near170seconds), still with an unnecessary remote fragment. The tight case remains disconnected with stock exhausted for both, failing near148seconds. These selected cases demonstrate real service improvement and a remaining route-assembly failure, not population optimality or a solved city strategy. Preserve plots, HTML, rawframes andsources in wait-repair/selected-replays/. Auditor now accepts explicit replay seeds; default evaluation behavior remains unchanged, active snapshots untouched.
