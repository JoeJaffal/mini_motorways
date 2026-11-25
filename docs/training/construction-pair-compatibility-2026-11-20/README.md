# Frozen test of building compatibility

On 20 November 2026 the user asked to test building pairs with no useful service connection. We interpreted the examples as isolated pairs where building should be unnecessary. Tested the final five-stage checkpoint, verified against its original build, on a separate native fixture host. The patch changes fixture reset geometry and occupant types only. Production code, action weights and checkpoints were preserved. [Fixture patch](pair-fixture.patch), [evaluator](evaluate_pairs.py).

Each case uses 100 seeds, 42000–42099. The blue house and blue destination control is paired with a blue-house/red-destination case with identical placement, driveway directions and stock. The other cases have two blue homes or two red destinations. Each board starts with no roads. The actor gets the clear-land exercise identity and the native legal construction mask. The two same-type cases are outside the original encoder's one-house/one-destination contract. The diagnostic adapter preserves actual parcel and road planes, uses the first visible member for an available role's approach and fills the absent role's approach and relative-coordinate planes with zeros. Mixed pairs use the unchanged encoder. The native world advances automatically after construction to the 180-second horizon or game over.

| Isolated pair | Boards where it built, highest probability | Boards with a physical link, highest probability | Boards with any deliveries |
|---|---:|---:|---:|
| Blue house and blue destination | 100/100 | 100/100 | 100/100 |
| Blue house and red destination | 100/100 | 100/100 | 0/100 |
| Two blue homes | 100/100 | 0/100 | 0/100 |
| Two red destinations | 100/100 | 23/100 | 0/100 |

The default sampled arm matched the counts except it physically connected 26/100 destination pairs. Mean road units used was 2.96 across every case and arm. The original clear-land interface cannot choose Finish. In an extra diagnostic arm, we exposed its existing Finish logit at every step without training. It still built on 100/100 boards in every case. The wrong-color arm chose Finish after building on all 100. The two-destination arm chose Finish after building on 23. No scene in this arm had a no-build policy outcome. The test comprised 1,200 runs and changed no weights.

Matched and wrong-color scenes had identical actual model tensors and masks for all 100 paired seeds in each mode. The first action also matched on every pair. The compact construction input omits building color, so color-only decisions are indistinguishable to this checkpoint. The simulator still enforces color for deliveries. The extension for same-type scenes is a diagnostic, and those results are conditional on that representation. This result does not conclude that homes or destinations should always be forbidden to share a road in a full city.

Proposed follow-up, pending approval: represent the visible colors and multiple parcels, expose a consistent stop or wait choice, and train with matched pairs and negative controls. Keep legal physical road construction available and measure road waste separately from native service. No training was run. [Per-run measurements](results.json), [aggregate and paired checks](metrics.json).
