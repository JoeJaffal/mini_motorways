# Road scarcity follow-up — 8 November 2026

User reports constantly running out of roads. Continuing checks-only authorization: no production changes or learning. Four small EmptyLab fixtures, no city growth, ordinary OriginalReference stock except one explicit roundabout grant; 5600 ticks total for reward timing, completed command in 4.95 wall seconds including build. Command: `.\tmp\dotnet\dotnet.exe run --project tmp/road-stock-check-2026-11-08/Check.csproj`. Exact scratch harness archived in road-stock-source; restore to tmp/road-stock-check-2026-11-08 to use its relative Compile path. No commercial-game live fixture executed.

## Measurements

| Check | Observed result | Interpretation |
| --- | --- | --- |
| Straight house (5,7) to shop access (12,7), six ordinary road cells | 25 roads ->19 | Costs six here. Inspected installed base GetConcreteCostForConnection returns one for each of five ordinary-to-ordinary edges, zero for the two building edges: five total. Thus this base-price fixture costs one extra here. Original value is derived from inspected logic, not a live inventory measurement; challenge modifiers excluded. |
| Redraw identical road |19 ->19 | No duplicate spend on this fixture. |
| Remove all six unused road tiles |19 ->25, zero pending | Immediate full refund works for unused ordinary roads. |
| Build one ordinary road, convert it to roundabout, remove unused roundabout |25 ->24 ->24 ->24; roundabout restored | Replaced ordinary road stock is lost in our accounting. AddRoundabout overwrites Infrastructure.Road; RefundOriginal only returns the roundabout token. Confirmed internal conservation defect. Installed AddRoundaboutEdit tracks concrete to mothball/release; exact live refund timing not tested. |
| Leave week-one choice pending from140 to280 seconds | Stock remains25; same two offers remain; choose offer ->45 (+20) | Unselected reward roads are not granted. Our viewer Update continues ticking with pending choices; MaterialInventory suppresses new offers until selection. At280 next overdue offer needs a subsequent tick. No evidence of permanent reward loss; selection delays stock, simulation does not automatically pause. Original pause/UI behavior not freshly verified. |

## Further source findings and limits

Starting stocks and package road amounts are exported numeric data, not an arbitrary global reduction: LA starts25, Beijing30, Tokyo25, Dar es Salaam25, London30. Most ordinary tool packages add20 roads; some motorway packages add10 and road-only packages30. Offer eligibility/weighting/history are not exact. GetExpectedUpgradePackageCount in inspected original uses elapsed weeks, consistent in broad structure; exact offer streams remain unvalidated.

FinishRemovals marks ALL remaining lane tiles and ALL ReturnRoute cells committed for every away-from-home car. This can delay refunds until future return travel, rather than just until a nearby car clears the deleted tile. Original lane retirement exists too; the excess delay compared with original is not measured here. Avoid claiming every delayed refund is a bug.

The original uses connection-based pricing, ours tile occupancy. The simple building-to-building chain overcharges by one; branches/cycles/merges may differ in either direction. Do not extrapolate one extra per arbitrary stroke, infer a percentage of user road shortage, or claim this fully explains the score gap. Provisional placement/supply can also change needed network length, unmeasured. Previous four-seed traffic diagnostics replenished road stock, so they could not diagnose normal inventory scarcity.

Confirmed actionable accounting findings: base-price mismatch and road stock disappearing on roundabout conversion/removal. Potential contributors: pending rewards during continuing play, route-wide delayed refunds, differing map layouts. No gameplay, installed game, save, settings, or training changes. Private installed extracts remain outside Git. Only scratch files and required durable documentation updated.
