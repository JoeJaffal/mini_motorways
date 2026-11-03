# gp-3.3: a hall of fame against selection noise

**Why.** In gp-3.2 the best rule (gp-2's, 245.1 on validation) left the elites after generation 2 and the population drifted. By generation 7 the rule sets it bred from validated 218–221 (EXPERIMENTS.md). The mechanism:

- Elites and validation candidates came from the racing top, and a rule only reaches the racing top through an 8-map first round.
- In generation 2, gp-2's rule scored 289 on its 8 maps and missed the top 16, so it never played the other 24 maps and was not kept.
- The rules that replaced it take clean routes freely. Their scores swing from map to map, so the best of 16 on 32 maps is mostly luck: racing scores of 250–303 against 218–237 on validation.

**User decision (2026-11-03):** pause gp-3.2 and run gp-3.3 with fairer selection; validation stays out of selection.

## Decisions

| # | Decision |
|---|----------|
| H-1 | **Reference-relative scores.** A fixed reference rule (gp-2's best as its never-clean 4-tree copy) plays all 32 training maps of every generation. A rule's score on a map is its trips minus the reference's trips on that map. That removes map difficulty, which swings 8-map means by ±40 trips, so scores from different generations can be pooled. |
| H-2 | **Hall of fame (8 rules).** Its members play the 32 training maps of every generation and keep every per-map difference they have collected. A lucky newcomer is re-tested on 32 new maps each generation and falls back; a strong rule cannot be knocked out by one bad 8-map draw. |
| H-3 | **Ranking by a lower confidence bound:** mean difference − 1 × its standard error. A rule that swings from map to map needs a larger mean to rank high, and that is exactly the failure seen in gp-3.2. The reference itself scores 0 with no error, so a rule ranks above it only when it is ahead by more than its standard error. Ties go to the larger mean, then the smaller rule. |
| H-4 | **Candidates each generation:** the members, the racing top 16 and the reference. Candidates whose games this generation are identical (trips, seconds, commands on all 32 maps) count once, keeping the better-ranked one, so near-copies cannot fill the hall. The best 8 form the new hall. |
| H-5 | **Elites and validation come from the hall.** The 3 elites are its top 3; the 3 rules validated per generation are its top 3, so a newcomer reaches validation only after the hall ranks it high. Validation never feeds back into selection. Breeding (tournament on first-round scores) is unchanged. |
| H-6 | **Generation 0:** the hall starts with the reference and the seed texts, so each seed gets a full 32-map test. |
| H-7 | **Opt-in.** `hof = 0` (the default) plays the gp-3.2 loop exactly and writes checkpoint format 3; `hof > 0` writes format 4, which older code refuses. Cost: up to 9 rules × 32 maps more per generation, much of it cached (members in the population already play the first 8). |

## As built (after review, 2026-11-03)

A review ran the old and new code side by side and found no correctness bugs. The loop with `hof = 0` is unchanged job for job, old runs resume unchanged, and changing only the validation games leaves the hall and the population unchanged. It found these weaknesses, all fixed:

- **Copies.** A smaller copy that played a member's games in a lucky generation could replace the member's long record with its own 24-seed one. Now copies are resolved before ranking: a member (the longest record first), then the reference, then the racing top. A text that leaves the hall, or is dropped as a copy, keeps its record in an archive (checkpointed), so a text that comes back does not start afresh.
- **Best-of-16 luck.** The best of 16 newcomers is about 1.8 standard errors lucky, more than the 1-standard-error penalty. Now a **probation** applies: elites are taken from re-tested members first (members since an earlier generation), then the rest of the hall, then the racing top. Validation takes re-tested members only, falling back to the hall's top when newcomers took every place. Generation 0's hall (reference and seeds) counts as re-tested.
- **Float ties.** Bounds and means are compared rounded to 9 places, so float noise cannot decide an exact tie.
- **Too few extra seeds.** `hof` needs at least 2 extra seeds (newcomers are scored on those only).
- **Resuming an old run with explicit default flags** (`--hof 0`, `--hof-se 1`) was refused, because config.json had no such field. Missing fields now compare against their defaults.
- **Short hall.** Elites fill up from the racing top when the hall holds fewer than `elites`.

## Setup of the run

As gp-3.2 (4-tree rules, same stop rule and validation) plus `--hof 8 --reference gp2-best-noclean.txt`. Seeds: gp-2's never-clean rule and gp-3.2's five best validated variants (245.0, 244.8, 244.2, 243.3, 237.7). Choosing those seeds by validation is a mild use of the validation maps; the final scores come from the held-out maps.
