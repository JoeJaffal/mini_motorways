# Selected city regression replay

Selection was fixed before replay: lowest scenario/action RNG among games that scored with focusedrun01 but scored zero after run02. Seed184000001. Both frozen replays exactly reproduce the evaluation counters; models/native host hashes are checked in selection.json.

Parent scored36 and lasted316.85seconds. Continuation scored0 and ended147.35seconds. At30seconds parent retained6road units, continuation0. Both produce extra branches; continuation spends its opening stock without delivering to the initial red destination and still has no delivery at native failure. This is a selected failure illustration, not the average game or proof that all extra training harms learning. Later generated layouts can diverge as construction changes; the common starting seed is not an identical late-board counterfactual.

The replay supports rejecting the continuation as the starting point for the Wait repair. It also shows the unresolved placement/driveway-completion problem: learning when to Wait alone cannot guarantee useful routes. Trace JSON/HTML and plotted comparison are retained, and the image was inspected.
