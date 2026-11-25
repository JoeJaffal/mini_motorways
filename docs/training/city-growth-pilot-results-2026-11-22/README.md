# One-hour growing-city PPO result

The user launched the [full-city pilot](../city-growth-pilot-launch-2026-11-22/README.md) on `Maskable-PPO`. The run used 32 Los Angeles workers and native delivery reward. It added 798,720 decisions in 3,617 seconds, averaging 220.8 decisions/s and completing 1,707 training episodes. The halfway save added 397,312 decisions. The final save added 798,720. The best training episode scored 186. Both checkpoint hashes and the starting hash matched their recorded identities. The frozen actor tensors also matched exactly.

## Paired review

All 72 frozen games reproduced the assigned city and action seed for each of the three models. The 24 review seeds were separate from training.

| Measure | Repaired start | Halfway | Final |
| --- | ---: | ---: | ---: |
| Mean deliveries | 84.04 | 76.46 | 73.88 |
| Cities scoring | 20/24 | 21/24 | 22/24 |
| Mean paid roads | 82.46 | 76.75 | 78.42 |
| Mean paid units outside observed assigned trip routes | 35.58 | 33.25 | 38.67 |
| Share of total paid units outside observed assigned trip routes | 43.2% | 43.3% | 49.3% |

The paired delivery changes averaged −7.58 at halfway and −10.17 at the end. Their 95% paired bootstrap intervals were −35.54 to +20.96 and −30.21 to +8.71, respectively. Absolute paid units outside routes were lower at halfway, alongside lower total construction and lower mean deliveries. Their share was essentially unchanged at halfway and higher in the final comparison. Each paired change in absolute outside-route units had a bootstrap interval that included zero. Routes are measured from observed vehicle assignments over the game. Future demand and trips between observations can limit this proxy.

Keep the repaired starting checkpoint as the current city reference. The later-city learned correction yielded more scoring cities in this sample but did not establish better score and road use together. Preserve both local pilot saves for comparison. No further training was started.

[Raw paired reviews](evaluation-games.jsonl) · [Evaluation summary](evaluation-summary.json) · [Road-use calculations](analysis.json) · [Run and checkpoint state](state.json) · [Manifest](manifest.json).
