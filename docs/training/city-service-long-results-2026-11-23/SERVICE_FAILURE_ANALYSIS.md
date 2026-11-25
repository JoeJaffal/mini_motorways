# Where the final policy lost deliveries

Follow-up on 23 November 2026 after the user asked what went wrong in `city-service-long-01` on `Maskable-PPO`. Reanalyzed the existing [matched games](games.jsonl) from the [eight-hour run](README.md).

| Measurement across 24 matched cities | Training start | Four hours | Eight hours |
| --- | ---: | ---: | ---: |
| Total deliveries | 2,365 | 2,424 | 1,851 |
| Deliveries to destinations that arrived after first score | 1,635 | 1,681 | 1,206 |
| Median game length in seconds | 476.58 | 514.48 | 454.25 |
| New destinations arriving with stock available | 77 | 86 | 83 |
| Of those, number that received a delivery | 69 | 75 | 66 |
| Of those, number that stayed unserved | 8 | 11 | 17 |
| Unserved despite positive stock at arrival and at least 90 seconds of follow-up | 7 | 9 | 14 |

Later service accounts for 429 of the 514 missing deliveries at eight hours versus the warm start. The final checkpoint also ran shorter games and saw 12 fewer new destinations, so delivery totals are affected by exposure time. The positive-stock misses persisted when restricting to arrivals with at least 90 observed seconds afterward. In that subset, the warm start served 64/71 positive-stock arrivals, the four-hour checkpoint served 72/81, and the final served 60/74. Evaluation was capped at 600 seconds.

The measured issue is worse service to new destinations even when the policy had some road stock at arrival. City layouts and survival diverge with policy play. A positive stock at arrival does not prove a legal matching route was affordable or that the stock was still available when it was needed. The paired review disabled route feasibility estimation. Late activation, irrelevant road placement, later stock spending and inability to reach the destination remain possible mechanisms. A targeted next check would replay the misses, annotate the first affordable matched route and log the decisions immediately afterward. No model state changed in this reanalysis. [Counts and source hash](service-failure-analysis.json).
