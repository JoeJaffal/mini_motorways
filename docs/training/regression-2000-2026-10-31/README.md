# Development regression diagnosis - 31 October 2026

Measured: user-run frozen seed2000 comparison reproduced protected235 trips at
792.35s versus final83 at469.7s. Both natural failures, unchanged weights. Protected
174 macro decisions, final102; each trajectory has8 states where the two policies'
argmax choices differ under identical observations and masks.

First ordinary command difference is index140 at140s,9 trips, identical state:
protected chooses upgrade index1 (type3 amount2 plus20 roads), final index0
(type4 amount1 plus20 roads). Inventory confirms protected gained2 traffic lights;
final gained inventory slot4 instead. Protected choice probabilities .516/.484;
final reverses preference .476/.524. Small preference changes can switch argmax.
Protected later builds lights at(12,12),235s and(20,8),466s. Final builds none.

Final policy fails at destination0,(16,8), demand10/capacity6, overcrowding50.025s;
several vehicles have crossing/approaching-priority waits around80-104s. Protected
survives longer but also eventually fails (destination14,(21,8),overcrowding50.025s).
On final trajectory at405/410/415s, route choices exist: protected would choose a
route while final chooses wait. Thus this case does not demonstrate complete
absence of planner options; their effectiveness is untested.

Inference: upgrade/tool availability and later route-versus-wait choices are
specific candidates for the regression, not a measured causal attribution. First
choice is near a probability tie, not proof of training instability or internal
reasoning. Recommend one isolated counterfactual: frozen final policy, force only
first differing upgrade to protected choice at140s, then resume normal decisions.
Do not globally ban upgrades or change rewards from this single exposed map.
No full counterfactual, new evaluation, replay verification or training executed
by assistant. Raw command traces remain local; archived policy decisions, replays,
protocol, outcome and first command difference preserve the compact evidence.
This is development diagnosis, not unseen-map improvement evidence.
