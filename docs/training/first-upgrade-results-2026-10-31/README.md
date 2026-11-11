# First-upgrade causal comparison - 31 October 2026

User completed the prepared test. Baseline reproduces83 trips/469.7s, zero lights.
Changing only the final policy's first upgrade at140s to choice1 produces266 trips/
838.3s, two lights, +183 trips. Both terminate naturally; intervention applied,
checkpoint files and policy tensors unchanged. Script guards require original
baseline command sequence, identical intervention state and legal replacement.
No training or assistant-run simulation occurred during result inspection.

Changed policy independently builds at(12,12), command ending236s, and(13,13),
ending348s. Baseline fails destination0 at(16,8). Changed game fails destination20
at(9,9), demand14/capacity9, overcrowding50.02235. Original protected policy scored
235, so final policy with one overridden choice exceeds that single-map score by31.
It is an intervened policy result, not a new unassisted checkpoint selection.

Causal interpretation: under this frozen policy and exposed seed, the upgrade
intervention changes total outcome substantially. Later light, road, offer and
spawn feedback is included; this does not isolate light physics or assign all183
trips solely to lights. It does not prove generally better upgrade preferences,
robust learning, or universal need for lights. No global upgrade ban/rule adopted.

Engineering recommendation: investigate upgrade representation/action utility,
especially packages for tools this restricted agent cannot deploy, and test a
single explicit upgrade-handling change against the protected checkpoint on a
predeclared development set before another long training run. Exact change and
budget remain undecided; retain228-development protected checkpoint. No long job
launched. Full command traces remain local in output/experiments/first-upgrade-2000-01;
small raw outcome/protocol, macro decisions and replays archived here. Replays
have not additionally been verified in native/headless playback in this inspection.
