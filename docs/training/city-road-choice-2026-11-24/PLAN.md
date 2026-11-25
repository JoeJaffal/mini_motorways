# Road-choice-only diagnostic, 24 November 2026

User authorized the proposed bounded diagnostic with “Go ahead”. Engineering choice: freeze both learned Wait corrections at their zero-output initialization; retain trainable relational/spatial road heads, shared spatial encoder and critic. Same whole-city initial weights and relative learning rates as the prior joint run. This is a controlled comparison, not continuation of the trained joint candidate. All older checkpoints remain intact. No planner, imitation, reward change or native simulator change.

Four rollouts × 16 workers × 512 decisions = 32,768 decisions; repeated cities 184000000–184000007, continuing 600-second truncation, bridges, native delivery reward, LR .0001, road scale .3, spatial/value scale .1, value coefficient .00001. No long run authorized by this diagnostic alone.

Checks: exact initial policy/value parity; frozen Wait tensors and Wait probability on shared observations after an optimizer update and after training; changed conditional road preferences; checkpoint round-trip and actual optimizer steps. Evaluate 8 repeated and 8 separate cities with 2 action RNGs each, using the previous reference and joint-run paired suites. Separate cities are already development data, not fresh confirmation. Selected replay anchors remain 184000000/193251 and 184000003/193254. Restore joint learning only if evidence supports improvement; otherwise retain the reference and report the limitation.

Restriction: freezing a nonzero visual Wait head would allow the shared encoder to alter its output. Preparation therefore requires zero final layers for both Wait corrections. The three-group optimizer starts fresh from the zero-step initialization; historical timestep counters are preserved. Its first group is a trainable road head so the trainer's Adam-step counter remains valid.

Additional predeclared check, before candidate results: repeat the prior 32-action-RNG opening probe on layout 184000000 at 180 seconds (RNG 194000–194031). Compare cached reference and joint results. This isolates opening sampling reliability on one known layout, not new-city generalization.
