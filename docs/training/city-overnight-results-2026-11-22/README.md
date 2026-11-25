# First eight-hour growing-city PPO result

The user ran the [eight-hour launcher](../city-overnight-launch-2026-11-22/README.md) on `Maskable-PPO`. It finished 7,008,256 decisions and 16,197 episodes in 8 hours and 5 seconds of active learning, averaging 243.3 decisions per second with 32 workers. The simulator was Los Angeles with native delivery reward, ordinary roads, Wait and automatic weekly road stock.

## Learning and selection

The first 100 training episodes averaged 21.84 deliveries and had 40 zero scores. The last 100 averaged 89.07 and had nine zero scores. Median survival rose from 202.1 to 441.0 seconds. The best score during training was 186 and 1,557 episodes reached the 600-second cap. These windows track the sampled workload as it changed over training.

The predeclared development review evaluated the start plus eight candidate checkpoints in 432 frozen games. It selected `city-006234112-96926793.zip` at 6,234,112 decisions, about seven hours into training. Its sampled mean on 24 development seeds was 101.75 versus 35.46 at the start and 88.92 at the final checkpoint. The selected checkpoint scored on 22/24 sampled development cities and the start scored on 21/24.

## Reserved comparison

| Mode | Starting mean | Selected mean | Starting cities scoring | Selected cities scoring | Median survival, start → selected |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sampled | 32.19 | 95.44 | 24/32 | 28/32 | 259.75 → 475.68 s |
| Greedy | 0 | 21.50 | 0/32 | 25/32 | 144.90 → 172.55 s |

Sampling improved the score on 26 cities, tied on three and lost on three. The paired mean gain was 63.25 deliveries with a 95% paired bootstrap interval of 43.31–82.91. The sampled selected checkpoint peaked at 175 and reached the 600-second cap in nine games. Four sampled games still scored zero. This establishes a score gain in the road-only Los Angeles setting. Transfer to another map, sustained play beyond 600 seconds, learned weekly choice and other tools are open.

Keep the development-selected checkpoint as the road-only reference. Keep the frozen initialization for future comparisons and treat the reserved suite as an evaluated benchmark for this run.

[Training windows](training-by-100-games.csv) · [Development summaries](development-summary.json) · [Reserved per-game data](reserved-episodes.jsonl) · [Reserved summary](reserved-summary.json) · [Run state and checkpoint hashes](state.json). Model weights, the compiled host, and the full training logs remain local under `output/`. All saved checkpoint hashes and the evaluation seed suite hashes were checked.
