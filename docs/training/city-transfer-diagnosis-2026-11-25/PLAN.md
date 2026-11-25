# Authorized native-score expansion comparison

## Hypothesis and controls

Hypothesis: practicing both completing a connection and reserving useful capacity for a later pair, while retaining real-city exposure, improves subsequent service. Start from the preserved original city-whole-initial-01/start.zip, SHA7eb605e4e465b9143e095e367abe0a01285b8ace05843aaac80bd48b5f049027. Newer policies remain saved but are not promoted. Starting from this exact trained reference is not a random restart; optimizer state is loaded as saved (the original residual initialization has zero Adam steps).

Arms: city-only control versus expansion-balanced (eight city workers,four offset two-arrival workers,four tight single-connection workers). Both use native completed deliveries only. No per-road cost, imitation, route planner, reference edit or simulator modification. The curriculum arm uses task-homogeneous minibatches after the smoke revealed strongly different advantage distributions. City-only minibatches are naturally homogeneous. This compares the complete curriculum recipe, not task composition in isolation.

Both:16workers,512steps,32rollouts=262144added decisions, batch128,four inherited epochs, base LR.0003,value coefficient1e-5,gamma/GAE1, inherited entropy.01/KL.03 and actor/critic relative rates. Value weight matches the recent gradient-balanced recipe; the original checkpoint's serialized.5is explicitly overridden in both arms. Keep Adam and policy weights from the checkpoint. Native city horizon600with normal truncation bootstrap; finite lessons60seconds terminate without continuation bootstrap. Same existing observation/action interface and legal bridges for city play. No hidden task ID or future spawn information is added.

Training seeds215000000onward. The parent checkpoint's stored sampling seed is restored and logged by the trainer. Save after every rollout; evaluate at65536,131072,262144added decisions. Do not stop for a single uncertain interim score. Abort for invalid data/nonfinite losses/process failure or10minutes without progress. All checkpoints remain local, with hashes archived.

## Evaluation and success interpretation

Fresh initial practice suite216000000–031,two action RNGs each, in single-offset and offset-pair tasks:128games per checkpoint. After repeated checkpoint use this is a development suite. Initial measured single success32/64; first pair39/64; both pairs20/64. Later pair placement survives61/64; missing pairs are failures. Baseline always exhausts the pair task's mean14.25road units. Record first/later/both service,native score,stock and outside-observed-route construction.

City suite remains184M/185Mdevelopment layouts (16cities,two RNGs each),600seconds,bridges enabled. Reuse the identical verified original baseline126.09375with30/32scoring, and run city evaluation at every selected checkpoint for both arms. Keep practice and city curves separate. Cluster bootstrap by city/layout, retaining paired RNGs,12000draws. Compare candidate versus original and expansion versus equally trained city-only control.

No automatic promotion, fresh confirmation or further run follows. Improvement must include city performance, not merely lesson success or fewer roads. A finite flat curve does not prove impossibility; continued improvement can justify a separately chosen extension. Multiple training seeds and fresh city confirmation remain required before recipe-level confidence or deployment claims.

## Checks and preservation

Twelve exact replay matches and native reward ledgers are archived. Existing native fixtures/host are unchanged; hash matches the previously checked104-suite host. Stage addition only changes task assignment and diagnostic labels; ordinary stages retain their selection rule. First smoke uses217Mseeds; second task-batch smoke218M. Both disposable smoke checkpoints are excluded from the comparison. Existing task-buffer tests verify transition/mask/return preservation and task sampling; saved smoke reload checks verify trainable/frozen tensors and optimizer state. All command lines, source snapshots, small metrics and output manifests are retained. Model ZIPs/native binaries remain local-only. No pull/reset/commit or file deletion.

Expected runtime is several hours for both arms and evaluation. This is an exploratory training budget, not a guaranteed convergence threshold or a promise of high city scores.


## Launch checks completed

Four existing task-buffer/reporting tests passed. Both disposable8192-decision smoke runs completed256Adamupdates; checkpoint reload verified finite tensors, changes confined to strategy/value entries and unchanged inherited prior. The second uses task-homogeneous minibatches; its first64audited updates include{'single-connection': 16, 'city': 32, 'two-arrivals': 16}. Neither smoke checkpoint seeds the experiment. Paired reporting identity checks passed with six synthetic curves. Original checkpoint SHA remains unchanged. Sources and native host will be frozen before launch.
