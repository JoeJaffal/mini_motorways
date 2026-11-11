# User-confirmed design decisions

Entries are written from the user's answers, one mechanic at a time. Ask the user before
adding an answer or extending an entry with a new design decision. Existing implementation
notes in `FIDELITY.md` are provisional technical observations, not user-approved descriptions
of the original game's behavior.

## 001 — Construction availability and cumulative spending

**Classification:** Intentional change from the original game's resource model.

### Original behavior

The detailed description of the original resource model is awaiting the user's answer and
reference verification. This entry does not establish its exact inventory or refund rules.

### Our intended behavior

- Construction items have unlimited availability. Spending is tracked instead of limiting
  the number of items the player or agent can use.
- The counter represents all construction spending incurred, including construction that
  has subsequently been removed.
- Demolition does not refund prior spending: removing infrastructure does not undo its cost.
- A budget limit is not currently imposed. The spending counter allows a budget constraint
  to be introduced later.

### Rationale supplied by the user

Real construction planning works with a budget to achieve the best outcome, rather than a
fixed inventory of road pieces and upgrades. Making items unlimited while measuring their
cost moves the environment toward that budget-based planning model and prepares it for
future budget constraints. Preserving past spending after demolition follows the same logic:
the original construction cost has already been incurred.

### Future option, not an active rule

Demolition itself may incur an additional cost later. The user raised this as a possibility;
no demolition charge or amount has been selected.

### Status

- Intended behavior and rationale: confirmed by the user's conversation answers.
- Current implementation: unlimited construction, cumulative spending, no demolition refund,
  and no additional demolition charge.
- Original-game behavior: not yet documented as verified.

## 002 — Provisional construction prices

**Classification:** Parameters chosen for our spending model.

### Original behavior

No original-game price equivalents are established by this entry. The original resource
model still requires a separate user answer and reference verification.

### Our intended values

| Item | Cost |
| --- | ---: |
| Road tile | 1 point |
| Traffic light | 5 points |
| Bridge tile | 10 points |
| Roundabout | 8 points |

### Basis supplied by the user

The values are somewhat arbitrary for now. The user asked ChatGPT to suggest reasonable
values and selected these as provisional starting values. They are not established here
as measured real-world costs, original-game values, or experimentally validated prices.

### Status

- Values and their provisional basis: confirmed by the user's conversation answers.
- The simulation currently charges these amounts for successful construction. A traffic
  light adds 5 points to the cost already incurred for its underlying road.
- Bridge charging is 10 points per water tile, provisionally confirmed by the user.
  A crossing spanning three bridge tiles therefore adds 30 points to cumulative spending.
- No additional price rationale, calibration method, or final pricing decision is assumed.

## 003 — Motorways excluded for now

**Classification:** Intentional omission from the original game.

### Original behavior

The original game includes motorways. Their detailed mechanics have not been documented
or verified in this entry.

### Our intended behavior

Motorways are excluded from the simulator for now.

### Rationale supplied by the user

The user considers both the game's motorway implementation and the underlying concept
unrealistic. Excluding them also simplifies the simulator. This records the user's design
judgment, rather than asserting an independently established finding about realism.

### Future option, not an active requirement

Motorways may be reintroduced later. No future design, pricing, or implementation has
been selected.

### Status

- Exclusion and rationale: confirmed by the user's conversation answer.
- Current implementation: no motorway construction tool or infrastructure type.

## 004 — House-based cars as the traffic foundation

**Classification:** Retain the original's basic house-and-car model as the foundation.

### Original behavior discussed with the user

Community gameplay guides describe two reusable cars per house, trips to matching-color
destinations, and a return to the originating house before another trip. These descriptions
have not yet been verified through controlled tests in the user's installed game.

Sources discussed:

- [Kierstin Jones — General gameplay](https://www.kierstin-jones.com/mini-motorways-general-gameplay)
- [Community strategy guide](https://steamcommunity.com/sharedfiles/filedetails/?id=2553726183)

### User's decision and rationale

Keep this simple house-based trip model as a foundation for understanding real-life traffic:
people want to travel somewhere, and different people want to reach different destinations.
In the user's experience, about two cars per house produces enough traffic for this purpose.
The model is useful as a simplified foundation, rather than a complete account of urban travel.

### Status and limits of this decision

- Retaining the basic model and its rationale: confirmed by the user's conversation answer.
- Confirmed current rule: exactly two reusable cars per house. This matches the current
  baseline, which has outbound, service, return, and home stages.
- Varying household fleet sizes remains a possible future option, not a current requirement.
  The user does not expect that variation to make a meaningful difference for now and chose
  to retain two cars in every house. No future distribution has been selected.
- Exact dispatch priorities, parking durations, and redispatch timing remain unverified.
  This entry does not approve the prototype's numerical timing defaults as original behavior.

## 005 — Color-specific destinations and avoiding separated networks

**Classification:** Preserve color matching; plan an additional training penalty.

### Original behavior discussed with the user

Cars serve destinations matching their house's color, as described in the community guides
listed in entry 004. Original-game dispatch details remain subject to reference testing.

### User's decision and rationale

Retain color matching. Colors give cars a specific purpose: a car must reach its appropriate
destination, which may be far away. Without this restriction, trips could reduce to whichever
nearby house can supply a car, removing an important network-planning challenge.

No demographic or other real-world meaning has been assigned to the colors.

### Intended additional training rule

The user wants a penalty if the model separates colors into independent road networks,
effectively treating the city as separate color-based layers and managing each independently.
The aim is to discourage that strategy while retaining color-specific destinations.

### Status and unresolved details

- Color matching and its rationale: confirmed by the user's conversation answer.
- Current simulation: cars are dispatched only to matching-color destinations.
- Penalty intent: confirmed; not implemented.
- Confirmed scope: penalize completely disconnected color-based road networks only.
  Connected networks whose colors use different routes are not separately penalized for now.
- Rationale supplied by the user: mixed neighborhood placement is expected to create natural
  pressure to mix roads and traffic. This is the user's design expectation, not a verified
  property of the current fixed-map prototype or a newly approved city-generation algorithm.
- A connecting road therefore removes the complete-disconnection condition, even if cars
  do not actually use it. No shared-road usage requirement is imposed by this decision.
- Component classification, treatment of temporarily unconnected buildings, penalty magnitude,
  and application timing still require user answers. Do not infer that every road must serve
  every color or that all disconnected road components are automatically violations.
- Penalty timing is deliberately undecided. The user's intuition is that the choice may depend
  on whether training uses reinforcement learning or an evolutionary approach. Neither a
  training method nor during-construction versus final-evaluation timing has been selected.

## 006 — Preserve the home–destination–home trip cycle

**Classification:** Retain the original's basic trip cycle.

### Original behavior discussed with the user

The community gameplay guide cited in entry 004 describes cars leaving home, visiting one
matching-color destination, and returning to their originating house before another trip.
Exact service and departure timings still require reference testing.

### User's decision and rationale

Preserve this cycle: home → one matching-color destination → the same home → available
for another trip. The user considers the original cycle a good representation of everyday
real-life travel and wants to keep it unchanged at this level.

This records the user's modeling judgment; it does not claim that all real-world journeys
follow this pattern.

### Status and limits

- Trip cycle and rationale: confirmed by the user's conversation answer.
- Current baseline implements outbound, service, return, and home stages with reusable cars.
- Multi-destination trips and departing for another destination before returning home are
  outside this confirmed cycle.
- Exact parking/service duration, departure scheduling, and route-selection rules are separate
  decisions. The prototype's current defaults are not established as original-game behavior.

## 007 — Demand-driven departures

**Classification:** Retain the original's demand-driven departure rule.

### Original behavior discussed with the user

Community gameplay guides cited in entry 004 describe a matching-color destination's demand
as the trigger for a car to leave home, rather than a scheduled daily departure.

### User's decision

Keep the original rule: cars depart in response to demand at a matching-color destination.
Do not introduce scheduled departures, such as a morning commuting schedule, under this decision.

### Rationale supplied by the user

Changing departure timing could make the model more realistic, but the user prefers to stay
as close to the original game as possible. They value how it simplifies difficult topics such
as departure timing and traffic analysis into a manageable model that, in their judgment,
captures useful effects of real-life traffic. Preserving that simplification is the reason
for retaining demand-driven departures.

This records the user's modeling judgment, not a measured finding that the game produces
the same results as a real-world traffic model.

### Status and limits

- Demand-driven departure rule: confirmed by the user's conversation answer.
- Current baseline dispatches available cars when a reachable matching-color shop has
  unreserved demand.
- Exact dispatch priorities, departure delays, and demand-generation rates remain subject to
  reference verification. Retaining this rule does not validate the prototype's defaults.

## 008 — Retain demand buildup and overcrowding failure

**Classification:** Retain the original's demand-and-failure mechanism.

### Original behavior discussed with the user

The community gameplay guide cited in entry 004 describes destination demand accumulating,
an overcrowding timer appearing when demand becomes excessive, and the game ending if the
timer expires before enough demand is served.

### User's decision

Keep the original mechanism: unserved shop demand accumulates, overcrowding can trigger a
timer, and failure to recover before the timer expires ends the episode. Do not replace this
with an evaluation-only penalty that allows the episode to continue indefinitely.
No separate rationale was supplied for this particular decision.

### Status and limits

- Retaining this mechanism: confirmed by the user's conversation answer.
- The current baseline has demand accumulation, an overload threshold, and episode termination
  after sustained overload.
- Original thresholds, timer progression, recovery behavior, and demand-generation rates still
  need reference verification. The prototype's current numerical values are provisional and
  are not approved as exact replicas by this decision.

## 009 — One shop size for now

**Classification:** Current scope restriction; larger destinations remain a future option.

### User's reference experience

The user reports that the version they played had one shop size. This describes their
experience; it does not establish which upgrades or destination sizes exist in all versions
or modes of the original game.

### User's decision

Use one shop size for now. Keep larger or upgraded, higher-demand destinations in mind as
a possible future feature, without enabling them under the current decision.

### Status

- One-size scope and future option: confirmed by the user's conversation answer.
- The current baseline uses one destination size and does not implement destination upgrades.
- Exact demand behavior is a separate matter; one size does not establish a demand rate.

## 010 — Avoid inherently impossible demand scenarios

**Classification:** Scenario-feasibility requirement.

### User's decision and rationale

Do not force a loss by generating demand that the available households and cars cannot
possibly serve. The user gave an illustrative mismatch between a shop requiring 15 visitors
per minute and an available supply of only 4. These are examples, not selected scenario
parameters or a defined unit for available supply.

### Status and unresolved details

- Avoiding inherently impossible demand scenarios: confirmed by the user's conversation answer.
- Confirmed feasibility criterion: each scenario must be serviceable with a sufficiently good
  road network. A poor network may still produce congestion and an episode loss; feasibility
  is not a guarantee that every network or policy succeeds.
- No feasibility algorithm, capacity margin, demand cap, or household-spawn rule has been
  selected. This requirement is not yet enforced by the prototype's fixed demand generator.
- Reusable car count alone is not a visitor-per-minute capacity: outbound travel, service,
  return travel, and departure availability determine repeat-trip throughput.
- How to construct or validate a sufficiently good reference network, treatment of temporary
  demand bursts, and acceptable spare capacity require further user answers before being specified.

## 011 — Buildings appear gradually

**Classification:** Gradual city growth in the intended simulation.

### User's decision

Houses and shops should appear gradually during an episode, rather than all buildings
being present from the start.

### Status and limits

- Gradual appearance of houses and shops: confirmed by the user's conversation answer.
- Current prototype: a fixed set of buildings is placed at reset; gradual spawning is not
  implemented yet.
- Initial building counts, spawn timing, placement, color selection, and house/shop sequencing
  still require user answers. No specific original-game spawning algorithm is established
  by this entry.
- Gradual spawning must respect the confirmed scenario-feasibility requirement in entry 010.

## 012 — Preserve original building-placement behavior

**Classification:** Replication target for building placement.

### User's decision

Follow the original game's building-placement behavior as closely as it can be verified,
rather than defining a separate placement scheme.

### Status and limits

- Original-style building placement as the target: confirmed by the user's conversation answer.
- The original's exact placement rules have not been established or tested in this entry.
  Do not substitute the prototype's fixed layout or infer a specific random-placement algorithm.
- Gradual spawning remains required by entry 011, and generated scenarios must satisfy the
  feasibility requirement in entry 010.
- Confirmed priority: first investigate whether the original game safeguards scenario
  feasibility. If it does, replicate its verified handling.
- If the original does not prevent inherently impossible scenarios, prioritize our feasibility
  requirement over exact replication. The user's rationale is to reduce the luck factor and
  avoid losses caused by an impossible scenario rather than network decisions.
- This does not establish that the original has or lacks such safeguards. Its behavior remains
  unverified, and no particular fallback algorithm (such as delaying shops or adding houses)
  has been selected.

## 013 — Fixed 50 × 30 tile map for now

**Classification:** Current map-size decision; expansion deferred.

### User's decision

Use a fixed map of 50 columns by 30 rows for now. Keep the option to expand the map later;
no expansion schedule, trigger, or maximum future size has been selected.

### Original-game reference

The user described 50 × 30 tiles as the original game's size. This is recorded as the user's
reference, not an independently verified claim about every original map, mode, or version.

### Status

- Current target size and future expansion option: confirmed by the user's conversation answer.
- The current prototype is 26 × 18 tiles; changing it to 50 × 30 remains implementation work.
- Buildings should still appear gradually within the fixed map, as specified in entry 011.

## 014 — Recreate original map layouts, starting with the supplied Los Angeles reference

**Classification:** Original-map terrain layouts as the current reference.

### User's decision and reference

Use maps from the original game for now, rather than inventing new river layouts.
The user supplied the screenshot below and tentatively identified it as Los Angeles.
Visible labels include Los Angeles River, Los Angeles Harbor, Santa Monica Bay, and
San Gabriel River, supporting that identification.

The user-supplied Los Angeles terrain screenshot remains in the local source project; the image is not tracked in this repository.

### Status and limits

- Using original map layouts and this screenshot as a starting reference: confirmed by the
  user's conversation answer.
- Reference image: preserved in the local source project, outside the files committed here.
- The screenshot supplies visible terrain geometry, not a verified 50 × 30 collision map.
  Tile alignment, buildable boundaries, and the construction behavior of park areas require
  reference verification; do not silently infer exact gameplay masks from appearance alone.
- No terrain tracing, tile-mask conversion, or map implementation has been completed under
  this documentation entry. The prototype still uses its earlier straight-river scenario.
- Additional original maps have not yet been individually selected or supplied.

## 015 — Variation between training episodes remains undecided

### User's position

The user considers training on varying cities potentially acceptable, given the intention
to avoid luck-based, inherently impossible scenarios. However, they explicitly leave the
decision undetermined for now.

### Status and limits

- No choice has been made between repeated identical city scenarios and varying building
  locations or appearance times across episodes on a fixed terrain map.
- This does not approve a randomization algorithm, a training-city distribution, or a change
  to the selected terrain reference.
- The feasibility requirement remains a design requirement, not a verified guarantee of the
  current prototype. Do not describe the existing generator as already free of luck-based losses.

## 016 — Retain eight-direction roads

**Classification:** Retain the original's road-direction model.

### Original behavior discussed with the user

The community strategy guide cited in entry 004 describes road segments in eight directions:
north, northeast, east, southeast, south, southwest, west, and northwest.

### User's decision

Keep all eight directions, including diagonals, rather than restricting roads to horizontal
and vertical segments. The user's affirmative answer was interpreted as retaining the
original option, consistent with the established replication preference.

### Status and limits

- Eight-direction roads: recorded from the user's conversation answer.
- The baseline supports cardinal and diagonal neighbor links, with provisional restrictions
  around building parcels and existing road corners.
- Exact connection, crossing, turn-geometry, and diagonal cost-accounting rules are separate
  matters that have not been established by this decision.

## 017 — Two-way roads now; one-way roads remain a future option

**Classification:** Retain the original's ordinary two-way road model for now.

### User's decision and reference

Start with two-way ordinary roads, with one lane in each direction, following the original
model discussed with the user. One-way roads may be added later; they are not part of the
current requirement. No additional rationale or future one-way-road design was selected.

### Status and limits

- Two-way roads and deferring one-way roads: confirmed by the user's conversation answer.
- The current baseline allows travel in both directions and draws an offset for each
  direction. It does not yet implement verified lane-level movement and turn connectors.
- Driving side, intersection priorities, lane geometry, and passing behavior remain separate
  matters requiring original-game verification and further user answers.

## 018 — Automatic driving; infrastructure control only

**Classification:** Preserve the original-style separation between construction and driving.

### User's decision

Cars drive automatically. The player or learning agent controls infrastructure rather than
individual vehicles, following the original behavior discussed with the user.
Individual-car steering, acceleration, braking, or direct vehicle orders are not agent actions
under this decision.

### Status and limits

- Automatic driving and infrastructure-only agent control: confirmed by the user's answer.
- The current baseline dispatches and moves cars automatically and exposes construction
  actions separately from simulation stepping.
- This decision defines the control boundary; it does not establish the prototype's routing,
  yielding, signal handling, or car movement as verified replicas of the original algorithms.

## 019 — Explore two unsignalized-intersection rule options

**Classification:** Alternatives to investigate; no final selection yet.

### User's decision

Keep two options to explore for yielding and priority at intersections without traffic lights:

1. The original Mini Motorways behavior.
2. Lebanese traffic law.

### Status and limits

- Investigating these two alternatives: confirmed by the user's conversation answer.
- Neither option has been selected as the final behavior or implemented as a verified rule mode.
- The original game's exact priority rules still require reference testing.
- Confirmed meaning of the Lebanese-law option: official legal right-of-way rules, not observed
  driving habits. Specific rules must be established from authoritative, current Lebanese legal
  sources before implementation; none are asserted or verified by this entry.
- This decision concerns unsignalized intersections. It does not automatically change traffic
  lights, roundabouts, driving side, or other vehicle rules.

## 020 — Original traffic-light behavior now; realism changes deferred

**Classification:** Preserve original-style automatic traffic lights for now.

### User's decision

The learning agent controls construction, like a human player of Mini Motorways. It does
not control signal timing or phases. Keep traffic-light behavior as in the original game
for now, subject to verifying that behavior.

### Future option

The user may change traffic-light behavior later to make it more realistic. No replacement
signal algorithm, definition of realism, or new agent control has been selected. This future
option does not authorize extending the agent's actions beyond construction.

### Status and limits

- Current target and future option: confirmed by the user's conversation answer.
- The baseline switches signals automatically, but its fixed phase durations, directional
  grouping, and clearance interval are provisional and not verified original-game behavior.
- Exact phases, timings, approach handling, and interactions with queues still require
  original-game reference verification.

## 021 — Explore original and Lebanese-law roundabout rules

**Classification:** Alternatives to investigate; same approach as unsignalized intersections.

### User's decision

Explore two options for roundabout behavior:

1. Original Mini Motorways behavior.
2. Official Lebanese legal right-of-way rules relevant to roundabouts.

Neither option is selected as the final rule set yet. As clarified for intersections, the
Lebanese-law option means formal legal rules, not observed driving habits.

### Status and limits

- Exploring both options: confirmed by the user's conversation answer.
- Original entry yielding, circulation, exits, and lane behavior require reference verification.
- Applicable Lebanese legal rules require authoritative, current legal sources before any
  specific rule is documented as verified or implemented.
- The baseline's single-node reservation and circular visual island are not a verified
  roundabout simulation. Neither candidate rule set has been implemented as a verified mode.
- This decision does not change the confirmed infrastructure-only agent control or select
  new roundabout geometry, lane counts, costs, or footprint rules.

## 022 — Original bridge placement and traffic behavior

**Classification:** Preserve original bridge mechanics, with the confirmed spending change.

### User's decision

Follow the original game's bridge-placement and bridge-traffic behavior. Retain our separate
cost rule of 10 points per bridge tile and unlimited construction availability.

### Status and limits

- Original-style placement and traffic as the target: confirmed by the user's answer.
- The original's precise span, connection, approach, placement, lane, and vehicle rules still
  require reference verification. This decision does not establish those details.
- The current baseline permits bridge tiles on empty water cells and uses its ordinary road
  traffic logic on them. Those implementation choices are not yet verified replicas.
- Construction cost remains cumulative and demolition does not refund prior spending.

## 023 — Road removal during active trips: pending original-game verification

**Classification:** Undecided behavior requiring reference investigation.

### User's decision

Leave the handling of road removal during active car trips undecided until the original
game's behavior is verified. The user did not select immediate removal or deferred removal.

### Status and limits

- Deferring the decision pending reference verification: confirmed by the user's answer.
- The current prototype queues removal while a vehicle occupies or is entering the tile.
  This is an existing provisional implementation, not an approved final rule or verified
  original-game behavior.
- Verify which vehicles retain access, whether whole trips or return routes remain committed,
  and when removal actually completes before proposing the final rule to the user.
- The separately confirmed cumulative-spending rule still applies: demolition does not refund
  previous construction costs. No additional demolition charge has been selected.

## 024 — Original-style car assignment and route selection

**Classification:** Replication target, with exact rules pending verification.

### User's decision

Aim to reproduce how the original game assigns available cars to matching-color shops and
chooses their routes. Cars make these decisions automatically; the learning agent continues
to control infrastructure only.

### Status and limits

- Original-style assignment and routing as the target: confirmed by the user's answer.
- Assignment priorities, distance or travel-time weights, tie-breaking, treatment of congestion,
  and route changes during a trip still require original-game verification.
- Do not assume that the original always picks the nearest house, geometrically shortest
  route, or least-congested route without supporting evidence.
- The baseline currently iterates available cars, chooses a reachable matching shop with
  unreserved demand using geometric route length, and recomputes routes at nodes. These
  are provisional implementation choices, not verified replicas or separately approved rules.

## 025 — Original-style shop access, parking, queues, and service

**Classification:** Replication target, with detailed mechanics pending verification.

### User's decision

Reproduce the original game's shop entrances, parking spaces, queues, and time spent at
a shop. Retain the separately confirmed single shop size for now.

### Status and limits

- Shop access, parking, queue, and service replication targets: confirmed by the user's answer.
- Entrance and exit geometry, parking-space counts, parking occupancy, queue behavior,
  service duration, and the exact point at which demand is fulfilled require reference testing.
- The current baseline uses a building cell and a provisional service dwell. It does not yet
  implement verified physical parking spaces, driveway queues, or original access geometry.
- Decorative parking marks in the viewer are visual elements, not evidence that functional
  parking mechanics have been replicated.

## 026 — Original-style car movement

**Classification:** Replication target, with detailed behavior pending verification.

### User's decision

Match the original game's car speed, acceleration, braking, following distance, and turning
behavior as closely as they can be verified.

### Status and limits

- Original-style movement as the target: confirmed by the user's answer.
- Whether and how acceleration, braking, speed changes, spacing, and turn-dependent behavior
  are modeled in the original still require reference observation. No numerical values or
  particular motion algorithm are established by this decision.
- The baseline's fixed travel speed, minimum same-edge spacing, and visual lane offset are
  provisional. They are not verified original-game behavior or a complete lane-level model.
- This entry does not resolve the separate original-versus-Lebanese-law alternatives for
  unsignalized intersections and roundabouts.

## 027 — Original-style demand generation and progression

**Classification:** Replication target, subject to scenario feasibility.

### User's decision

Follow the original game's shop demand rates and how those rates change over time, while
respecting the confirmed safeguard against inherently impossible scenarios.

### Status and limits

- Original-style demand generation and progression as the target: confirmed by the user's answer.
- Exact rates, timing, bursts, progression, and relationships to city growth require reference
  verification. No specific stochastic process or numerical schedule is established here.
- Preserve the current single-shop-size scope. This decision does not enable larger or
  upgraded destinations, which remain a future option under entry 009.
- As established in entry 012, replicate verified original feasibility safeguards where
  available; otherwise prioritize serviceable scenarios. No fallback algorithm is selected.
- The baseline's seeded intervals and overload settings are provisional and do not yet
  implement verified original demand progression or enforce the feasibility safeguard.

## 028 — Separate original-style trip score and construction spending

**Classification:** Preserve the trip-score metric and add a separate spending metric.

### User's decision

Keep the original game's trip score alongside a separate cumulative construction-spending
counter. Leave the training reward or evolutionary fitness formula undecided for now.

### Status and limits

- Separate trip score and spending counters, with training formula deferred: confirmed by
  the user's answer.
- The original's precise score-award event and accounting still require reference verification.
  The baseline awards one trip point on outbound arrival; this timing is provisional.
- Spending retains the confirmed prices and all-construction-ever-placed accounting,
  without demolition refunds. No additional demolition charge or active budget cap is selected.
- No weighting between trips, spending, waiting, survival, or the intended disconnected-color
  penalty has been chosen. Keeping separate metrics does not define a combined objective.

## 029 — Original-style game clock and pacing; no weekly material grants

**Classification:** Preserve simulation-time progression and remove inventory-related grants.

### User's decision

Retain the original game's day/week clock and gameplay pacing. Remove weekly material
grants because construction availability is unlimited in our version.

### Status and limits

- Original-style clock and pacing, without weekly material grants: confirmed by the user's answer.
- Exact conversion between simulation time, days, and weeks, and its relationship to spawning
  and demand, still require original-game verification.
- The baseline currently tracks elapsed simulation seconds; it does not implement a verified
  original-style day/week calendar or original pacing.
- Viewer pause, step, and playback-speed controls are existing inspection tools. This entry
  does not establish their settings as replicas of the original or change training-time stepping.
- Removing material grants does not choose a new periodic reward, budget allocation, upgrade
  menu, or calendar-triggered mechanic.

## 030 — Failure-only episode endings for now

**Classification:** Current episode-termination rule.

### User's decision

For now, an episode ends through the original-style failure condition. Do not impose a
maximum simulated duration as an additional episode-ending rule.

### Status and limits

- Failure-only termination without a fixed duration limit: confirmed by the user's answer.
- The intended failure mechanism is the demand/overcrowding behavior in entry 008; exact
  original thresholds, recovery, and timing still require verification.
- The baseline world terminates on its provisional overload condition. Its evaluation and
  benchmark tools currently use finite tick/time limits for bounded runs; those tool limits
  are not approved episode rules. Future training code must distinguish interrupted or
  truncated runs from actual environment failure.
- This decision does not prevent manually pausing, resetting, or closing the viewer.

## 031 — Implementation defaults while questions remain open

**Classification:** User-authorized implementation policy; not a final decision on undecided mechanics.

The user requested: "apply everything you recovered and we talked about, if something is undecided apply from original but keep in mind that we still need to decide."

Implement recovered original behavior provisionally where the user has not chosen a replacement. Keep unresolved alternatives visible and do not invent the user's rationale. The technical implementation/approximation register is maintained separately in IMPLEMENTATION_STATUS.md. Earlier confirmed decisions remain in force.

## 032 - Two versions, original as the primary target (24 October 2026)

The user wants an exact original-game replica and a separately tweaked version for training comparisons. Implementation uses one shared core and two isolated selectable rule sets rather than two duplicated games. OriginalReference is the default but is explicitly unfinished; the name does not certify exactness. Original mechanics can be investigated and implemented without further design questions. Existing custom changes must not be applied to the original target.

## 033 - Custom objectives and out-of-scope choices

The user's primary objective is staying alive / keeping the city running. Less waiting and lower construction cost are secondary rewards. No numerical weights or ranking between these secondary goals were supplied. Learning-method selection (worksheet 1) and color-separation penalty design (worksheet 6) do not matter for this task; do not implement a learner or invent a penalty. Retaining raw diagnostics is not a training reward.

## 034 - Custom run options and driving rules

Include both a fixed map with varying events and varying maps with varying events as running options. Seeded repeatability remains useful for comparisons. Use original rules at both unsignalized intersections and roundabouts. The Lebanese-law alternative is not an active task. The current available map crops are Los Angeles, Beijing and Tokyo.

## 035 - Custom feasibility, grace and demolition

For inherently impossible scenarios, the user's choice is rejection rather than changing demand to make the scenario easier. Keep the 30-second new-shop grace. Keep the retire/clear/remove approach to road deletion. Spending never refunds, as previously confirmed. The implementation's estimated-capacity rejection screen is provisional technical work; it is not a proof of impossibility.

## 036 - Custom prices updated

Road tile = 2; traffic light = 5 additional; roundabout = 8; bridge water tile = 10. This supersedes the road price of 1 in entry 002 for the custom version. Prices do not apply to the original-reference inventory system. The user did not supply a new pricing rationale.


## 037 - Separate Original and Custom apps (24 October 2026)

The user chose two different apps: one for the original copy and one for Custom. This supersedes entry 032's single-app packaging. Build two separately named executables with fixed rules and no viewer version selector. Share the simulation source rather than duplicate traffic logic. OriginalReference remains unfinished; this packaging choice does not establish original-game parity.

## 038 - Five-map Original replication scope

The user selected Los Angeles, Beijing, Tokyo, Dar es Salaam and London, then authorized work toward an exact Original replica. Standard-play behavior on those five maps is the active target; adding motorways is required for Original. Custom remains a separately launched ruleset. This is authorization to implement and compare; it is not evidence that exact parity has been achieved.

## 039 - Continue implementation of remaining replication systems (25 October 2026)

The user authorized implementation of the remaining systems and reference comparison work. The installed game remains read-only. Original destination scheduling, upgrades and single-lot layouts are implemented from observed numeric values and independently expressed rules; Custom keeps its existing one-size baseline. The generator is checked against values invoked directly from the installed assembly. These changes do not certify exact-game parity or finish London train/station gameplay.

## 040 - Continue with shared car parks and London trains

The user's repeated request to proceed authorizes the remaining implementation work. Original now has functional shared two-color lots, multiple entrances, train movement, station demand and crossing closures. London rail ordering is checked against the installed component. Placement, parking/rail splines and full-run comparisons remain provisional. Custom retains its existing lot and demand behavior. The original installation stays read-only; component probes do not constitute a full-game recorder.

## 041 - Accept current parking approximations for now

After the entrance-center and conservative concurrency differences were explained, the user accepted keeping the current parking behavior for now while work proceeds on other differences. This does not certify exact parking or cancel the overall Original replication target. The repo cleanup request also authorizes documenting and committing the completed work, organizing maintained source, and pushing it to the user repository.

## 042 - OriginalReference learning experiment on mohammad (28 October 2026)

The user selected structured simulator data, all ordinary tools and trial-and-error
learning, initially one city and a provisional 1,000-trip goal. Training work must
live on `mohammad`; `main` remains the playground. The later user requests include
repeated practice on one seed, best-game native playback, live diagnostics and
parallel workers. A four-worker, four-hour run was explicitly authorized and
completed. These decisions do not replace Custom's earlier objectives or certify
OriginalReference fidelity. Full chronology, implementation choices, failures,
analysis and measured outcomes are in
[the training history](../../training/EXPERIMENT_HISTORY.md).

## 043 - Preserve every update, decision and analysis

The user requires all material updates, decisions, reasoning and performance
findings to be documented, including information originally presented in the
model PDF. Keep historical decisions/results and record superseding changes;
do not maintain only a current-state summary. Preserve reports, graphs and
small measurement sources in version control. Distinguish user choices from
engineering choices, evidence from hypotheses, and unknowns from measured facts.
The [training evidence index](../../docs/training/README.md), experiment history,
AGENTS.md and contributor guide implement this continuing requirement.

## 044 - Authorize useful-connection reward shaping (28 October 2026)

The user explicitly approved adding a carefully designed reward for establishing
useful connections. New training defaults to bounded discounted potential-based
connectivity shaping plus completed trips; the earlier trip-only mode remains
selectable. The chosen coefficient/cap and anti-loop accounting are engineering
choices, not new user-specified numeric weights. Actual trips still determine
best games and held-out scores. Rules, input channels and tools are unchanged.
No shaped learning run was started. See the
[design, audit and limitations](../../training/REWARD_SHAPING.md) and history T15
for rationale/evidence; faster learning remains unmeasured.

## 045 - Model chooses construction directly; route planner is not the target (3 November 2026)

User decision: after discussing how the hybrid generates routes and lets the
model choose among them, the user explicitly rejected the planner idea and asked
to put direct model control into the plan. The target learns tools, construction
locations/endpoints/order, removal/reconnection, upgrades and waiting itself.
Ordinary execution and legality checks remain environment code; hand-coded route
generation or strategic action selection must not supply the target's solutions.
The old hybrid is preserved as a comparison baseline. This supersedes the v2
planner-led development path, not historical results or accepted simulator rules.

Engineering plan: audit/reuse existing primitive all-tools adapter, version its
observation/action/return/cursor contracts, prove actual direct construction on
small withheld lessons, then select algorithms and expand to full network repair.
Optional offline demonstrations are not a deployed planner and are not required.
Direct control is a user preference, not measured evidence of higher scores.
No simulator behavior, rewards or checkpoints changed and no training launched
by this planning edit. [Roadmap v3](../../docs/training/learning-roadmap-v3-2026-11-03/README.md)
and training history T63 preserve scope, dependencies and prior evidence.

## 046 - Advance notice before longer training (4 November 2026)

The user explicitly asks to be told before starting longer training. State the
purpose, expected duration and stopping limits before such a run. Short probes
must also have explicit bounded budgets, never silently extended. This request
does not authorize a new long run. AGENTS.md records the continuing instruction.
For issue8 a disclosed four-run classroom pilot finished35.50s total learning;
the proposed next8min learning/10min inclusive pilot has NOT started. Historical
game rewards/checkpoints and simulator rules remain unchanged. See historyT68–T69
and [lesson evidence/proposal](../../docs/training/direct-learnability-2026-11-04/README.md).

## 047 - User launches training from terminal commands (4 November 2026)

The user approved the proposed classroom pilot but explicitly wants to launch
training sessions personally: provide the terminal line, then review the results
they return. This applies to diagnostic learning pilots too. The assistant may
prepare/test non-training setup, plans and commands but must not start training
on the user's behalf. AGENTS.md records the standing instruction. Approved pilot
is four fresh4096-selection/120s runs,480s learning/600s inclusive; no extension or
promotion. No run started during preparation. See historyT70 and the
[manual execution plan](../../docs/training/direct-manual-pilot-2026-11-04/README.md).


## 048 - Inform user before changes (6 November 2026)

User explicitly requests notice before changing anything. Explain intended
changes before editing; authorization to record and diagnose the completed run
does not itself authorize a different lesson, algorithm or training session.
All training remains user-launched under047. T73 records this review and its
proposed, unimplemented next diagnosis. No simulator behavior change.


## 049 - Preserve best evaluated model and replay for watching (6 November 2026)

User explicitly requests that the NEXT training run save the best because they
want to watch it. Preserve a checkpoint and matching exact-command replay,
selection metric/step/hash, plus separate final/error files. Engineering choice:
fit-only fixed screens, best means best evaluated snapshot, not a passed gate;
never select on final holdouts. Next-run recorder is opt-in and source-pinned,
not a training authorization. T77 records tests and a current short fit preview.


## 050 - Correct examples for a bounded teaching diagnostic (6 November 2026)

After completedPPOconstructiongates fail, user authorizes the proposed small
experiment: teach correct trainingexamples, testseparate layouts with model-
chosen actions. Offlineexamples are allowed for this diagnostic; the user's
rejection of inference-time planners remains. This is not authorization for
an automaticlearning session or largerdemonstration pipeline. Engineering
choice isfit-only set-valuedmaskedactor imitation, originalphysicalsuccess
checks, declaredteacher/sourcecost and no heldlabels. T85 preserves dataset/
loss/counters/limits/checks/manualcommand. User still launchesalltraining.


## 051 - Public high-score videos as optional teaching references (7 November 2026)

User permits researching YouTube high-score/world-record videos for useful
buildingactions. Publicsources may inform futureoffline lessons; any video-
derived label still requires reconstruction/ordinary-rule verification and
training-only provenance. This does not certify recordclaims, approve a planner
atplay or authorize assistant-run learning. T86 records metadata-only research
coverage, knownaccesslimits and unchangedcurrent192-example pilot.


## 052 - Consistent-order teaching diagnostic (7 November 2026)

User approves the proposed offline teaching order: unconnected goal first, then
join the supplied road end. This authorizes a bounded prospective dataset/run
preparation, not automaticlearning or runtimeforcedactions. Keep ordinarylegal
moves and modelchosen inference, physicalheldtests and best/replay requirement.
T88 records narrowercorpus/phaseweighting and matched50passes caveat; the old
two-direction labels remainphysicallyvalid. Userlaunches alltraining.


## 053 - Critical self-review and focused memorization diagnostic (7 November 2026)

User asks us to proceed with the proposed tiny first-click diagnostic and to
question our reasoning at every material step in this chat, flagging anything
off or inconsistent with the rules. This is a user preference/authorization for
preparation and critical review, not assistant-run learning. Engineering choice:
fixed one-case then gated four-case FIT memorization, warm versus scratch, with
explicit limits and no inference planner. T91 records prospective criteria,
checks and limitations; no capability result exists yet.


## 054 - Assistant execution until further notice (7 November 2026)

User cannot run commands and explicitly asks assistant to run work autonomously
while they sleep, through multiple justified roadmap steps. Supersedes decision047
user-launched-only restriction until further notice. Advance notices, explicit
bounded experiments, best/replay preservation, critical review and documentation
remain required. No permission to invent results or relax capability gates.
T92 begins the prepared tiny first-click experiment under a new launch plan;
historical T91 preparation stays historical.


## 055 - Empty-start full-route lesson audit (engineering choice, 7 November 2026)

Following authorized autonomous roadmap work, distinguish supplied-leg extension
from independent two-stroke construction. New opt-in FullRouteLesson removes
the scaffold, ordinary legaltools/stock and observedgoals remain; no runtime
witness/route hint. Deduplicate visiblegoalpairs/canonical offline labels before
teaching to avoid contradictions when scaffold-specific states collapse.
Explicit full-route observation schema; frozen64/44/6input-compatible probe
not automaticcheckpoint migration/PPOready. T96 records48feasibleFITcases,
freepolicy results and native demos; no full-route learning launched.


## 056 - Return to manual training; full-route preparation (7 November 2026)

User says they can run commands again; assistant commits to providing checked
commands and user accepts continuing the plan. Restore user-launched training,
ending decision054temporaryovernight exception (AGENTSupdated).
Engineering choice:48FITfullroutes/288newstates plus432unchangedextension
rehearsalstates, freshAdam/valuehead/counters from priorFIT-selectedbest250actors.
Runtimeactions stay modelchosen/ordinarylegal; onevalidcanonicaloffline order
isnot forcedatplay. BothBEST/FINALmustpassfullroute+priorretentiongates inboth
seeds. T97records checks/budgets; preparation doesnotlaunchlearning.


## 057 - Approved matched offline recovery comparison (7 November 2026)

User accepts T99targetedfix if it follows the existingplan. Implement within
roadmapv3directconstruction/offlinecorrections/retention (#8/#12/#15). User
launches learning. Engineering choices:bothFIT-selectedbest750sources, broader
124cleanFITcases, source-specificverifiedrepairprefixes, matched96batchallocation
(clean48/prior48 vsclean24/recovery24/prior48), fixed1000updates/bothseeds,
FIT-onlybest/replay andunchangedphysicalretentioncriteria plusold48FITguard.
No runtimeplanner/strategicmask, no algorithm/reward/simulatorchange. T100has
actualqualification/checks/budgets; no trainingstartsbythispreparation.


## 058 - Branch-consistent offline teaching and historical control reuse (engineering, 7 November 2026)

Following userrequestcontinueplan, T102audit finds canonicalmismatch isnot
alwaysbadfirstroad; continuationwrong-goalfailuresobserved. Within#8/#12/#15,
acceptcanonical+onephysicallyverifiedsource-preferredFITendpoint andteachits
matchingremaining-goalcontinuation. No runtimeplanner/maskchange. Reusecompleted
T100clean controls with hash/version/initialstate/samplerchecks; source750same.
TwoUSERruns only, fixedmatchedpractice, samephysical/retentiongates. T103records
non-learningqualification/checks; newlabelsets+stateallocationpackage notpure
loss-onlyproof. Userlaunchrequired; no trainingbyplanpreparation.


## 059 - Controlled goal-relative input ablation (engineering, 8 November 2026)

Within continued#8/#12/#15plan, T105localizesremainingfailures afterbranchdata
fix. Reuseexistinggoal/cursor-relativefeaturecandidate (+576), not a router or
newalgorithm. EarlierT78–T84noreliableextensionadvantage remainsvalid; teston
now-validatedfull-route/branchdata asunprovenhypothesis. SAMEsources/data/loss/
samplers/FIT-onlyselection/gates ascompletedT103branchcontrols; onlycandidate
newruns, newcolumnsinitialzero/matchedactor/valueoutputs. T106documentsfixed
budgetsandno-learningchecks; USERlaunchonly,no trainingbypreparation.

## 060 - User requests gameplay fidelity checks only (8 November 2026)

User reports high-800 original scores versus 200s here and rejects treating that difference as acceptable merely because exact replication was not guaranteed. Checks only; no gameplay changes or training. Fresh internal suites pass but do not validate difficulty. [Investigation](../../docs/training/gameplay-fidelity-check-2026-11-08/README.md) records measured parking access blockage, confirmed provisional supporting-house differences, mixed-direction demand omissions and missing matched original traces. Earlier parking acceptance remains historical; it is not a difficulty-parity approval. No new implementation choice made.

8 November road-stock follow-up to decision060: user reports constant road shortage. [Checks](../../docs/training/gameplay-fidelity-check-2026-11-08/ROAD_STOCK.md) confirm tile-vs-connection base-price mismatch and lost road stock on roundabout conversion/removal; redraw and unused ordinary-road refunds pass. Pending reward/retirement timing remain possible contributors. Checks only, no fix authorized or made.

8 November roundabout follow-up under060: user reports differing behavior. [Checks](../../docs/training/gameplay-fidelity-check-2026-11-08/ROUNDABOUTS.md) document priority comparator mismatch, reconstructed merge/conflict geometry and automatic corner connections. Bare directed ring passes; no matched throughput evidence or implementation change.

## 061 - Begin fidelity repairs and plan recorded-game comparison (8 November 2026)

User authorizes fixes, proposes uploading a complete original-game recording, replicating seed/choices and comparing scores. Accept comparison objective; seed recoverability/full spawn equivalence not guaranteed. Distinguish reconstructed visible-layout/action comparison from verified same-seed parity. First engineering patch conserves concrete replaced by roundabouts, refunds after old surface lane paths clear, protects repeated removal/rebuild;44 suites PASS. [Source/test/deployment record](../../docs/training/roundabout-concrete-fix-2026-11-08/README.md). Running player still old build; no training or score claims. Connection pricing and other fidelity work remain open; historical comparisons stay historical.

## 062 - Broader repairs verified and installed (8 November 2026)

User authorized fixing all reported issues. Connection-based concrete/refunds, parking boundary/lane clearance/merge reservations, supply curves/per-color cadence, demand/failure timing, reward weights and viewer choice pause implemented and tested.54 core,7 environment,6 reward,10 map-version checks; Original installed at usual path after prior app closed, backup local;5 player city smoke passes. [Full changes, intermediate failures and limits](../../docs/training/gameplay-fidelity-repairs-2026-11-08/README.md). Exact RNG/placement/traffic/process parity remains unvalidated; not all original replication work complete. No learning/promotion. Earlier roundabout tile credit superseded by replaced-connection credit. Corner shortcut finding qualified: original permits some such connections.

## 063 - Freeze for exact recorded-game comparison (8 November 2026)

User uploads screen-capture (2).webm and requests exact seed, decisions and timing, score comparison, no changes yet. Stop further gameplay/build/settings edits. Read-only video/local records audit confirms last failure HUD835; initial826 was a paused score and is superseded. No matching seed/journal found in scoped local search; existing exact-mode guard refuses original parity. [Evidence and missing capability](../../docs/training/recorded-game-comparison-2026-11-08/README.md). No matched simulator score, no fabricated zero/delta. Visible-event reconstruction asked asynchronously; no answer/authorization inferred. Required documentation only after freeze; no training.

## 064 - Custom seeding and visible-event replay (8 November 2026)

User explicitly supersedes063 freeze for custom seeding and reconstruction from uploaded video. Add numeric seed input plus JSON scheduled spawns/actions/offers and read-only replay, strict event rejection, display-only reference score. Simulator RNG carrier is video-hash-derived, not recovered original seed; visible reconstruction cannot promise original hidden state or exact timing. No gameplay tuning to835, learning or holdout use.58 core suites pass; video trace remains under validation. [Durable diagnostics and limits](../../docs/training/custom-video-scenario-2026-11-08/README.md).

064 continuation: corrected Unity offer serialization, player/headless agreement verified (draft24/297.45s/84, example4/80/5),58 core PASS; corrected player installed with previous app backup. Draft24vs835 is explicitly preliminary, not original parity; future696 events unvalidated after early simulated game-over. Dynamic red carpark waits>139s, static isolated control clears, so cause remains sequence-dependent/open. No further gameplay-rule tuning or training.

## 065 - Fix recorded early carpark blockage (8 November 2026)

User sees replay difference and authorizes playground tweaks. [Measured repairs](../../docs/training/video-performance-repair-2026-11-08/README.md): boundary lane omission bypassed entrance reservations; first fix exposed bay merge cycle; short merge sweep reservation with already-ahead priority resolves tested cycles. v1/v2 rejected on existing tests; v3 passes67 core,7 environment,6 reward,10 map/version checks. Identical297.45s inputs24/failure→30/no failure, red deliveries2→9;330s37/no failure. No demand/stock/seed tuning, training or original parity claim. Separate v8 trace hits CV diagonal rejection466.65s; original full draft remains historical/unvalidated. Player build pending; prefix330 provided.

065 deployment: corrected Unity player prefix37/330/99 matches headless and normal LA startup20s PASS. Installed after graceful previous-replay close, prior app backed up local; prefix330 reopened visibly/paused. Assembly SHA256896AF3A97E05E4450C5A7B0671CA81669BDFFF7D2DA88B2B9C6A93B636260578. Scope remains carpark traffic repair, not full original parity or accepted entire video trace.

## 066 - Require event-level parity; correct missing movement scale (8 November 2026)

User explicitly requires identical performance, not merely improved comparisons. [Audit and failing observations](../../docs/training/event-parity-2026-11-08/README.md). Installed rule audit confirms omitted movement factor3 (separate from route lane values) and ordinary weighted/motorway minimum lookahead. Correct these without fitting835;69 core PASS. First delivery25.15→17.45 vs original estimated17.418, but second~2.2s late/third~6.3s early: NOT IDENTICAL.330s candidate50trips vs prior37, not original parity. Preserve failed/history fixtures and rewardv3/v4; final player verification pending. No learning, seed fitting or hidden-state match assertion.

066 verification/deployment:69core/7environment/6reward-v4/10map-version PASS; Unity prefix50/330/99 and normal LA20s match/check pass, corrected player installed with local backup and prefix reopened paused. Original observed-event comparator exits1/NOT_MATCHED (2of3timings outside estimated intervals plus tick); exact behavior target remains unfulfilled. v4 ordinary fixture13trips/252.95s/253actions; v3(12)andv2(4) preserved. No training/score-fitting/promotion/source push.

## 067 - Validate replay input before further tuning (8 November 2026)

After user asks what now, engineering prioritizes video input review and makes no simulator-rule change this iteration. [Opening review](../../docs/training/replay-input-validation-2026-11-08/README.md): synthetic native-stub road edits/orphan cells removed, red native driveway west and observed user north turn corrected.16events/60video seconds(~90game). Manual topology/direction/stock checkpoints2/7old→7/7reviewed; player loader6/90/16passes, incidental score not parity. Full trace, exact timing/hidden state and actual wall-clock pause/2x playback remain unvalidated; original-event gate remains NOT_MATCHED. Reviewed JSON opened paused; no learning or binary/core change.

## 068 - Continue full input review independently (8 November 2026)

User accepts reviewed opening and explicitly authorizes continuing using their video and simulator without user timestamp review. [Ongoing full review](../../docs/training/full-replay-review-2026-11-08/README.md):55observed houses vs prior51, navy top/latergreen left entrance corrections,117diagonal candidates screened, dynamic parcel-time filtering and per-second registration. Strict v10–v13 diagnostics preserve failures/rejections, no grants or skipped inputs; v13alive286at832.95s then road-stock rejection, NOT valid835comparison. Native shared-endpoint behavior remains an open question. Engine unchanged/no learning; continue validation.


## 069 - Shared-lot transit and erased endpoint cleanup (8 November 2026)

Independent full-video work under068 identifies missing intermediate shared-carpark routing: source far-red is serviced before motorway edit while our prior route forbids any intermediate building. Private read-only rule evidence confirms shared circulation; independent physical-lane transit implemented with doubled path cost and no parking/delivery credit. Initial71core/7environment/6reward/10map checks PASS. Samev14earlyfailure295→335alive then strict material rejection; not a full835comparison. Input-specific rounded-curve false edge corrected, no stock grants. Deferred erased motorway endpoint blocks later spawn; targeted cleanup regression72PASS. Later v15reveals outside-turn shared gate deadlock, approach-boundary fix and bent mixed-flow test in progress. [Chronology, measurements, rejected hypotheses and limits](../../docs/training/full-replay-review-2026-11-08/README.md). No learning; installed69-rule app unchanged pending complete verification. Original parity remains NOT_MATCHED.


069 emergency-stop continuation: user explicitly stops all work and requests branch checkpoint/continuation plan. [Handoff](../../docs/training/full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md). Installed74verified; native motorway75PASS; common native endpoint77initialPASS then physical-access dedup correction untested. v20/75partial586at1185.95s,340/406events, NOT full835comparison. Late input corrections identified not applied; no77build or learning. Do not resume automatically.


8 November2026 — User requests missing-file review/handoff work. [Response](../../docs/training/full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). Fetched Aya1779c0b; packaged2368local payloads/video into verified924MiBZIP, kept out ofGit. No external upload, simulator changes, fixture update or learning. General native-rule intent distinguished from unproven implementation correctness; prior results remain historical/version-specific.


## 070 - Resume simulator repairs on a second machine (8 November 2026)

**User decisions.** Aya asked to continue and finish the stopped simulator update, remove gameplay bugs and protect the headless interface used by Evolved Rules and PPO, and requested a simulator version string so result caches never mix simulator versions. No training. The user is to be asked before any non-bug gameplay rule change, any run over 20 games, and any push. Mohammad confirmed (`8a4b447`) that the 75/77 native joins are intended general Original rules, asked for proof before any rule change or new fixture, and asked for all seven input corrections to be regenerated through the builder.

**Engineering choices** ([report](../../docs/training/simulator-repairs-2026-11-08/README.md)):

1. The reward-v4 change is the intended rule-77 join in ordinary play (isolated by single-rule variants), so a new fixture v5 was recorded; v4 stays historical.
2. A car's current `Waiting` is cleared on arrival home or in a bay.
3. Approach priority is not held by a car whose target is occupied by a stationary conflicting vehicle. This was chosen over a broader variant (any conflicting occupant) that changed many more decisions.
4. `simulatorVersion` is additive, starting at `2026-11-08.1` and now `2026-11-08.2`.
5. Replay input v21 is the builder plus only the handoff's seven corrections.

**Hypothesis outcomes.** The roundabout future-junction/yield-cycle hypothesis is confirmed (deadlock from t=1163 in v20). The idea that this deadlock caused v20's game-over is rejected (overcrowding at 11,18 started earlier).

**Open question for the user.** A physical gridlock at adjacent junctions 20,11-20,12 (cars inside a junction with no room to exit) ends replay v21. Preventing it would be a new traffic rule and has not been made.

**Superseding.** Decision 069's statements that source 77 is unverified are superseded: 77 passed, and the source now has 79 suites. Original parity remains NOT_MATCHED.


8 November2026 — User authorizes answering REQUEST_SPACE_CHECK_RULE. [Read-only original-rule audit](../../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md): conditional shared-exit gap chain(5states,>2vehicle lengths), inbound eligible-prefix arbitration, first-two-lane commitment, route-time registration and explicit blocking-cycle shoving verified. Installed green bypass on/straight-entry option off;45swait feature runtime state unverified.191e9adpartial filter is not an exact reproduction. No engine changes, original execution, learning or score claim; private source stays local.


## 071 - Replicate the original's junction entry arbitration (8 November 2026)

**User decision.** Replicate the original's space-checking logic, including its conditions, for the adjacent-junction gridlock, using Mohammad's existing read-only extracts rather than decompiling anything on this machine.

**Evidence.** [Mohammad's answer](../../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md): there is no blanket box rule; the original uses a conditional shared-exit space test, eligibility partitioning and blocking-cycle shoving.

**Engineering choices** ([report section 8](../../docs/training/simulator-repairs-2026-11-08/README.md)):

- OriginalReference only; Custom keeps the previous rules.
- A tight-gap tolerance of 0.01 tiles, because our follower holds the minimum gap exactly.
- The same-exit geometry check is kept after the space test, because our engine does not follow across merging lanes.
- Return routes are registered like any route.
- Not implemented: all-leader pushing, the stopped-candidate geometry argument and the 45 s escape.

**Supersedes** decision 070's stationary-occupant priority rule for OriginalReference.

**Open question for the user.** The carpark approach-gate lock at shared lot 20 (gate owned by a car queued behind the requester) ends the replays.


## 072 - Carpark gate measures every car at one point (8 November 2026)

**User decision.** Keep the engineered approach gate, but rank cars as the original ranks entry candidates (one distance measure), let blocking-cycle recovery see gate waits, and send Mohammad a note inviting a better approach. The user also watches the real game for supporting behaviour.

**Engineering choice.** The common point is Mohammad's existing reference, the start of the outside approach lane, now also used for cars passing through a shared lot (ranking, stopping and holding). Measuring every car to the entrance itself was rejected after a ParkingFlow overlap.

**Open questions to Mohammad** ([note](../../docs/training/simulator-repairs-2026-11-08/NOTE_CARPARK_GATE_CHANGE.md)):

1. Do carpark entrances use the original's chunk arbitration?
2. How does the original switch signal phases when green-phase cars cannot move?


8 November2026 — User requests original traffic-light/carpark follow-up. Read-only private-rule/config audit: nearby0.5tiles/min3/overtime1sconfirmed, but blocked-candidate early termination and commitment-age phase weights differ materially from simulator. Installed age multipliers carpark10/mothball4, same-chunk active-pair total penalty0.1; no max-green cap. Amber retains prior ActivePair in shown chunk permission logic; American non-crossing red-turn exception on. Carpark entrance/exit/internal paths use road chunks; no separate one-owner gate found in inspected classes; bay allocation separate. Full response/provenance in ORIGINAL_SIGNALS_CARPARKS_ANSWER.md. Reported408vs513GPresult not rerun, no causal attribution/engine edit/learning/deployment.

[Source-backed response](../../docs/training/simulator-repairs-2026-11-08/ORIGINAL_SIGNALS_CARPARKS_ANSWER.md).


## 073 - Replicate the original's traffic lights (8 November 2026)

**User decision.** Ask Mohammad for the original's light and carpark rules, measure stuck lights deterministically meanwhile, then implement his answer with failing tests first and rerun the lights on/off comparison.

**Engineering choices** ([report section 11](../../docs/training/simulator-repairs-2026-11-08/README.md)):

- OriginalReference only.
- The inbound-list order is approximated by registration time, then vehicle id.
- "Lane replacement" has no equivalent here.
- A light on a ≤2-lane tile still affects junction speed through `IsJunction`, as the original's controlled-chunk speed recalculation suggests.

**Superseded.** The previous OriginalReference signal weights and the all-red amber.

**Next.** Carpark entrance/exit chunk arbitration (Mohammad's B1–B4) before retiring the gate.


## 074 - Carpark chunk arbitration; keep the compensating gate (8 November 2026)

**User decision.** Start the carpark rebuild, push when done, and ask the Evolved Rules session to start a fifth genetic-programming generation (gp-5) on the improved simulator.

**Engineering choices** ([report section 12](../../docs/training/simulator-repairs-2026-11-08/README.md)):

- Our parking lanes are mapped onto the original's chunk kinds and arbitrated with the junction order.
- The gate is kept because removing it deadlocks the eight-car queue through our entrance geometry, per Mohammad's caution.

**Open.**

- Rebuild the entrance and exit connector geometry, then retire the gate.
- Bay chunks use the simple early-accept branch where they have two or fewer lanes.


## 076 - A red-light car may not hold the carpark gate (9 November 2026)

(075 is used on `main` for its simulator-only import.)

**User decision.** Investigate LA 3101 before gp-5 starts; keep `main` simulator-only.

**Engineering choice** ([report section 13](../../docs/training/simulator-repairs-2026-11-08/README.md)). Apply the original's eligibility rule (red-blocked candidates are not eligible) to our engineered carpark gate. A car held by a red light before its gate lane may not take or keep the gate, and the light is checked first. The gate itself remains an engineered compensation, as in decision 074.


## 077 - Local read-only original reference on this machine (10 November 2026)

**User decision.** Work on a separate branch, `fidelity-aya` (pushed to origin), in parallel with Mohammad; the better simulator is chosen later. Set up, on this machine, the same original-game code reference Mohammad works from, to investigate why the recorded 835-point Los Angeles game ends earlier and lower in the simulator. This supersedes decision 071's "rather than decompiling anything on this machine" for future investigation.

**Engineering choices.**

- Decompiled the user's own Steam install read-only with ilspycmd 8.2.0.7535 (9.x needs a newer SDK than .NET 8). `App.dll` SHA256 `76c9d906…c638` equals `REFERENCE_DATA.json`, so this is the build the existing work studied.
- Output is kept outside every Git repository, in `C:\Projects\490 - Project\mm-original-reference\`, with a README giving the regeneration commands. As before, no decompiled classes or assemblies are committed; only our independent code and numeric findings.

**Not yet done.** No engine change, replay or score comparison has come from this setup yet.


## 078 - First pin after four seconds for every destination (10 November 2026, `fidelity-aya`)

**Evidence.** In the original, both destination spawn paths call `DestinationModel.Initialize`, which sets the demand timer to `DelayBeforeFirstPinOfDestination` (4 s in the installed asset); nothing else writes the timer except the regular interval reset. The "3 s while the clock is under 1 s" branch only applies to a reset, which a 4 s timer never reaches. Our `InitializeDestinationDemand` instead gave every destination after time 0 a full demand interval (8–32 s), and a fidelity check asserted that.

**Engineering choice.** Start every destination's countdown at `FirstDemandDelay` (4 s); correct the fidelity check and the oscillation test to the original's behaviour. Simulator `2026-11-10.f1`.

**Measured** ([report](../../docs/training/fidelity-aya-2026-11-10/README.md)). Replay v21, 16 fixed phase sets: mean 576.6 → 606.1 trips, mean game over 1173 → 1190 s; fitted phases 642 → 665. 85 suites pass.


## 079 - Original carparks: continuous trips, no engineered gate (10 November 2026, `fidelity-aya`)

**Evidence.** Original `VehicleMovementProcess`/`ParkVehiclesProcess`: the outbound path ends on the carpark entrance lane; when the car moves onto the lane before it, a free bay (random) or a drive-through is chosen and the in-lot lanes are appended; after 3 s parked the car gets one path from its bay to its house. Carpark lanes are ordinary chunks arbitrated like junctions; there is no entrance owner, no whole-lot departure check and no body-clearance test. `RoadTileConnection.IntersectsOtherConnection` returns true for two connections with the same output, so in `WouldInboundVehicleCollideWithTraversingVehicle` a traversing car on a different lane with the same exit blocks entry after the space test (unless green).

**Measured before the change.** On f1, our trips stopped at every leg boundary (outbound→lot, lot→return), the gate serialised each entrance, and toggling the gate or the departure check off alone deadlocked: entering and leaving cars blocked each other through our body-clearance limiter. Details and toggle results in the [report](../../docs/training/fidelity-aya-2026-11-10/README.md).

**Engineering choices** (OriginalReference only; Custom unchanged).

- `ContinuousJourneys.cs`: entrance lane appended to the outbound path; bay or drive-through attached on the lane before it; return lanes appended when leaving a bay or driving through; stage changes at recorded lane indices.
- Removed the gate (decisions 074/076), `CanBeginBayDeparture` and the body-clearance step limiter; ordinary stop offset at entrances.
- Same-exit merge rule added to road and carpark chunk arbitration.
- The two body-overlap checks become "no two cars share a position" (centre distance ≥ 0.15 tiles), because the original has no body test; observed minimum after the change is above 0.2.
- The drive-through test waits for the car to enter the lot, since the decision is now made one lane earlier (original timing).

**Measured.** Simulator `2026-11-10.f2`: 16-phase mean 606.1 → 749.4 trips (616–804), mean game over 1190 → 1281 s, 4/16 runs reach the end of the replay; fitted phases 665 → 748 at 1279 s. 85 suites pass.

**Supersedes** decisions 074 and 076 (gate) for OriginalReference.


## 080 - Carpark lane speeds from the original's lane-speed rule (10 November 2026, `fidelity-aya`)

**Evidence.** The original's `GameBehaviourModel.GetLaneSpeed` applies to every lane, carpark lanes included: default speed 1, times 2/3 (right angle) or 1/3 (sharp or U-turn) by the connection's directions, times `intersectionSpeedMultiplier` 0.5 when the lane has more than one outbound lane. Applied to the `CarparkModel` connections: entrance 0.5, exit 1, end U-turns 1/3, aisle through lanes 0.5 (1 where only the end turn follows), bay entry 1 (45 degrees), bay lanes 1, bay exit 1/3 × 0.5. Ours used a flat 0.6 for every carpark lane.

**Engineering choice.** OriginalReference carpark lanes take these factors (`OriginalParkingLaneFactor`); Custom keeps 0.6. Simulator `2026-11-10.f3`.

**Measured.** 16-phase mean 749.4 → 772.5 (713–815), 6/16 reach the end of the replay; fitted phases 748 → 777 at 1296 s. 85 suites pass.


## 081 - Original lane speeds and movement details (10 November 2026, `fidelity-aya`)

**Evidence.** Original `GameBehaviourModel.GetLaneSpeed` and `VehicleMovementProcess` (installed constants from the `core` asset): the 0.5 intersection factor belongs to a lane whose outbound lanes offer more than one way (the approach lane), skipped when any outbound lane is signal-controlled or a roundabout lane, and for U-turn/roundabout lanes; turn factors are skipped for ring-to-ring lanes and lanes coming off a motorway; the roundabout multiplier applies to ring lanes only. Maximum acceleration is 0.9 w/s² if the current or next chunk is a roundabout, 0.8 if the current or next chunk is controlled or the car's driveway or near a motorway lane end, else 0.54; it doubles when blocked at a controlled chunk within two vehicle lengths. With no obstacle, from more than two vehicle lengths before an uncontrolled chunk with at least `NumberOfRoadsAtIntersectionToSlowDownFor` (3) roads (houses, carparks and roundabout lanes ignored), acceleration is capped as if following a car at `targetSpeedTowardsIntersections` (0.55) of the desired speed, deceleration exponent 1.6. A refused junction is a stopped obstacle at distance + (vehicle length − half the minimum gap).

**Engineering choices** (`OriginalMovement.cs`, OriginalReference only). As above. Our roundabout route cost keeps the ring speed, because our centre-to-centre step (1.41 tiles) at the ring speed gives the same cost (23 per quarter) as the original's ~1.16-tile arc at default speed. The roundabout speed check now uses a real ring lane. A third body-overlap check (recorded carpark prefix) becomes "no shared position" like decision 079; the case found was a car passing on the aisle beside a car starting to leave its bay (centre distance 0.243).

**Measured.** Simulator `2026-11-10.f4`: 16-phase mean 772.5 → 769.2 (645–807), median 783.5 → 791, 7/16 reach the end; fitted phases 777 → 774. These rules move speed in both directions; kept for fidelity. 85 suites pass.


## 082 - 45 s intersection escape and the original's arrival timing (10 November 2026, `fidelity-aya`)

**Evidence.** The installed `resources.assets` TextAsset `DefaultConfig` enables `MaximumWaitTimeAtIntersections` and disables `CheckForVehicleCollisionsWhenMerging`; the Steam config overrides neither. `RoadChunkModel.CanInboundVehicleEnter` therefore lets a car enter after more than `MaximumTimeToWaitAtIntersection` (45 s) since it committed to the lane (first among its next two path lanes), after the light and shove checks and before traversing vehicles and priority. `ParkVehiclesProcess` accepts an arrival (pin, score, overcrowd credit, parking timer) when the car enters its bay lane. `VehicleMovementProcess` makes a returning car wait for a destination as soon as it enters its driveway lane. Eviction from a full lot requires a destination of that lot with waiting (dispatched) demand.

**Engineering choices** (OriginalReference). `WaitedTooLong` in road and carpark arbitration; delivery and the 3 s timer on entering the `bay-park` lane (the timer keeps running to the bay middle); a returning car finishes at the start of its house tile lane; eviction uses `Reserved > 0`.

**Measured.** Simulator `2026-11-10.f5`: the 45 s escape alone 769.2 → 769.4; all together 16-phase mean 775.2 (605–806), 8/16 reach the end; fitted phases 800 at 1311 s (real 835 at ~1314.6 s). 85 suites pass.


## 083 - Pin relocation and the original failure-timer update (10 November 2026, `fidelity-aya`)

**Evidence.** `GenerateDemandProcess.GenerateTimerDemand`: when a destination's timer fires at maximum demand and `GameRules.AllowDemandRelocation` (true in classic rules), the pin goes to the nearest active same-group destination with room, else the nearest destination of any group, by squared distance between carpark top-left tiles. `FailureStateProcess` runs after `ParkVehiclesProcess`; arrivals increment `demandJustCleared`, consumed only in the overcrowding branch (timer capped at max − grace, then per arrival speed × 0.02 and timer − clamp(10% × timer × curve, 0, 3)); the next-frame timer is floored at zero; game over tests the current-frame timer.

**Engineering choices** (OriginalReference). `RelocationTarget` uses each lot's first destination cell as the anchor (an approximation of the original carpark top-left). `UpdateOriginalOvercrowding` runs after `UpdateVehicles`; `Deliver` only banks the arrival. Custom keeps the previous path.

**Measured.** Simulator `2026-11-10.f6`: 16-phase mean 775.2 → 775.1 (604–806), 8/16 reach the end; fitted phases 800 at 1310 s. Effects are confined to the last seconds before failure. 85 suites pass.

**Replay note (not a rule change).** The replay's destination spawn times put the red destination of plan window days 8–22 at 474 s and the red one of days 30–42 at 919 s, both after their windows close. In the original such delays add extra demand to that colour (`BalanceDemandFromFailedSpawns`), which may explain why the original delivered more pins early than our formula creates from the replay's spawn times. Its exact timing is not recoverable from the video, so the replay does not model it.


## 084 - U-turns only at dead ends; dispatch details (10 November 2026, `fidelity-aya`)

**Evidence.** `RoadTileSignature` gives a tile a U-turn lane only when it has a single road connection; elsewhere a car can turn around only through a driveway or a carpark loop, at ordinary lane cost (`Pathfinder` declares a `UTurnPenalty` but never uses it). `VehiclePathfindingProcess` re-paths from the car's committed lanes, so it never reverses in place. `DispatchVehiclesProcess` removes items while counting up in its loop for the last destination, dispatching ceil(n/2) per tick, and measures house cost from the end of the driveway lane.

**Engineering choices** (OriginalReference). `FindRoute` refuses a reversal unless the tile has one connection (no penalty there) and takes the heading into the start tile; `RefreshJourney` passes the current lane's heading; the cache key includes it. Dispatch quota and `FirstStepCost` as above.

**Measured.** Simulator `2026-11-10.f7`: 16-phase mean 775.1 → 777.8 (726–819; the 604 outlier is gone), 8/16 reach the end; fitted phases 799 at 1307 s. 85 suites pass.


## 085 - The original's lane-conflict test; retired motorway cost (11 November 2026, `fidelity-aya`)

(Decision numbers 085+ on the growth branch `fidelity-aya-growth` will be renumbered when merged.)

**Evidence.** `RoadTileConnection.IntersectsOtherConnection`, called with right-hand traffic and `smallIntersection = true` from `RoadChunkModel` for traversing and inbound checks, decides conflicts from the entry and exit sides only: same exit conflicts (unless crossing in front of a stopped or hot-swapping candidate is allowed and the entries differ), same entry never conflicts, an exact reversal never conflicts, a lane conflicts with the other's half-turn rotation (opposing left or right turns), otherwise the lanes cross when exactly one of the other's sides lies clockwise from this lane's entry through its exit. An audit scripted our sample-distance test against it on a 4-way tile: every same-entry pair conflicted in ours, opposing half-turn pairs did not, and on roundabout tiles the entry lane conflicted with the same tile's exit lane. `LaneModel` charges a mothballed lane 100000 in pathfinding; ours did not penalise a retired motorway when cars re-route.

**Engineering choices** (OriginalReference road lanes; carpark lanes keep the sample test). `ConnectionsIntersect` in `OriginalMovement.cs`, used by `Conflicts` and the inbound priority order (stopped candidate: speed below 0.0005 tiles/s, the original's 0.001 world-unit threshold). `FindRoute` adds 100000 for a retired motorway when retired links are allowed.

**Not adopted.** Removing a traffic light when its tile drops below three roads: the original counts pending roads, which we do not model, and on the replay our version removed a light the real game kept (mean 777.8 → 745.4).

**Measured.** Simulator `2026-11-10.f8`: 16-phase mean 777.8 → 796.7 (613–822), 15/16 runs reach the end of the replay; fitted phases 824, surviving to 1314.6 s (real 835, game over ~1314 s). 85 suites, five-map checks and training readiness pass.

**Open (audit, not yet done).** Roundabout ring split into 8 lanes with corner chunks (ours 4, so commitment reaches twice as far upstream); motorway end-tile lanes and arbitration at motorway starts; diagonal tile-corner chunks and crossing diagonals; traffic-light pair order and post-amber hold; roundabout chunks counting as controlled for the blocked-acceleration boost.


## 086 - Roundabout commitment reach and controlled roundabouts (11 November 2026, `fidelity-aya`)

**Evidence.** The original ring has eight lanes: a 57° arc on each ring tile and a corner-chunk arc between ring tiles (`LaneUpdateProcess`, `TileCornerModel`). A car is committed to a lane only while it is among its next two path lanes (`VehicleModel.IsCommittedToLane`), so a circulating car counts for ring tile T only from T−1. Our ring has four 90° lanes, so the same rule reached T−2 and circulating cars held priority over entering cars from twice as far. `RoadChunkModel.IsControlled` is true for roundabout chunks as well as signals, so the blocked-within-two-vehicle-lengths acceleration doubling applies at roundabout entries too.

**Engineering choice** (OriginalReference). In `Committed`, a ring lane reached from a different ring lane counts only as the immediate next lane; `blockedControlled` includes roundabout lanes.

**Measured.** Simulator `2026-11-10.f9`: 16-phase mean 796.7 → 809.3 (800–822), all 16 runs reach the end of the replay; fitted phases 820 at the end. 85 suites pass.


## 087 - Original motorway end tiles (11 November 2026, `fidelity-aya`)

**Evidence.** `LaneUpdateProcess` builds a motorway as a straight bespoke lane from the start tile's lane exiting in the motorway direction to the end tile's lane entering from it; the end tiles keep ordinary chunk lanes to and from that direction (`AddMotorwayAction.ValidTileDirectionFor`: the closest direction, or a neighbouring free one). The start-tile lane is arbitrated with the tile's other lanes and has a turn factor but no intersection factor (its single outbound lane is the motorway); the end-tile lane runs from the slot edge across the tile with no turn factor. Ours ran the fast lane from the start tile's entry edge to the end tile's centre, never arbitrated entry at the start tile, and gave cars half an end tile.

**Engineering choice** (OriginalReference). `OriginalMotorwayStart` in `OriginalMovement.cs` and the end-tile start point in `MakeLanes`. The slot is the closest of eight directions; the fallback to a neighbouring free slot is not modelled.

**Measured.** Simulator `2026-11-10.f10`: 16-phase mean 809.3 → 792.8 (741–809), 12/16 reach the end (four now fail at 1281–1309 s, near the original's ~1314 s); fitted phases 816 at the end. No stuck cars; waits are dominated by the shared-exit space test as before. 85 suites, five-map checks and training readiness pass.


## 088 - Signal pair order and rotation details; roundabout exit lanes (11 November 2026, `fidelity-aya`)

**Evidence.** `TrafficLightModel.CalculatePairs` scans directions from North (opposite pairs, then leftover pairs three steps apart, then singles); ours started at East. `NextValidPairIndex`: with inbound vehicles it takes the highest-weighted other pair, keeping the current one when none has weight; only with no inbound vehicles does it step to the next index (ours always stepped). `TrafficLightAlternatingProcess`: when lanes change and the active pair no longer exists, the light rotates immediately without amber and restarts its timer (ours took the first pair and kept the elapsed time). `RoadTileConnection.IsRoundabout` is true only for ring-to-ring lanes, so a ring tile's exit lane takes the 0.5 intersection factor when its next tile offers several ways (ours excluded every roundabout-tile lane).

**Engineering choice** (OriginalReference). As above in `UpdateSignalPairs`, `WinningPair` and `OriginalLaneSpeed`.

**Measured.** Simulator `2026-11-10.f11`: 16-phase mean 792.8 → 784.5 (747–808), 8/16 reach the end; fitted phases 784, failing at 1301 s (original ~1314 s). Traffic-light waiting is unchanged (44 car-seconds on the fitted run). 85 suites, five-map checks and training readiness pass.
## 089 - Original free-play building placement: weight layers and building influence (11 November 2026, `fidelity-aya-growth`, merged into `fidelity-aya` as f12)

**Scope.** OriginalReference free play only (`TrafficWorld` with growth). Custom and recorded replays (`CustomScenarioSession` forces spawns and disables growth) are unchanged; replay v21 gives bit-identical results to f7.

**Evidence (our reading of the original's building placer and spawning process).**

- Each placement reads one weight layer: the colour's house ("Supply") layer for houses, its destination ("Demand") layer for lots, the station layer for stations. Layers are keyed by type and colour; a definition painted for "all colours" has its own key that no colour placement reads. A tile outside the layer is forbidden; once the entry has failed more than five times it is allowed at weight 0.
- A tile must be driveable (buildable, not water or mountain), zoneable and free of content. Its weight is then scaled by nearby buildings, using per-colour distance maps filled 4-neighbour from house tiles and from the 2x2 destination tiles (not the parking strip), never entering water, mountain or rail tiles: weight 0 within one step of any destination or on a house tile. Houses: own destination within 7 multiplies by 0.425^(7−d); other-colour house within 7 by 0.9^((7−d)/2); own house within 7 by 0.6^(7−d) (grouping Far) or p^(7−d) with p = max(1.05, 1.3 − 0.035 × own houses within Euclidean radius 5) (Near). Lots: own destination within 12 multiplies by 0.6^(12−d) (Far) or 1.3^(12−d) (Near); the original's house term for lots requires 0 < d < 7 and d > 7 at once, so it never applies.
- Then: every tile in the 3x3 around a roundabout centre is forbidden; around every house the density map (painted in Los Angeles only; elsewhere all high) halves ring 1 (medium) or multiplies rings 1/2/3 by 0.125/0.25/0.5 (low); when placing a lot, the 3x3 around every house is forbidden and each own-colour lot multiplies Chebyshev rings 1–4 around its footprint by 0.0625/0.125/0.25/0.5; the footprint plus a one-tile ring of every lot is forbidden for houses and lots; a new lot's driveway may not use an existing lot's driveway tile.
- Every footprint tile must have weight ≥ 0; the placement weight is the footprint average. Every legal (tile, layout) placement draws uniform(0, average); placements are sorted by draw, highest first, and the first whose driveways can find a path away wins.
- Houses get a grouping when they are scheduled: a colour's first house Normal; later ones Near, becoming a new suburb (Far) with probability ((min − count) × 0.7)^1.2 below the minimum suburb count, else ((max − count) × 0.4)^1.4 below the maximum; min/max are the colour's suburb curves at days since its first destination, scaled by lerp(1, 4, clamp01((highest attempts among the colour's pending destination entries − 5)/5)). Lots use the plan's grouping (0 Normal, 1 Near, 2 Far).

**Engineering choices.**

- `scripts/export_placement_data.py` exports, for all five cities, the per-tile house/destination weights per colour (one character per tile, weight = digit/4; every installed weight is a quarter step), the density map, the unbuildable mask, the station layer and the suburb curves (all unweighted Hermite keys) into `OriginalPlacementData.cs` (numbers only).
- `OriginalPlacement.cs` implements the above in our own code. Our single-lot layouts 0–3 are the original's four single layouts; ordinary double lots use only our shared layouts 2 (vertical, carpark west) and 0 (horizontal, carpark south); stations keep all four shared layouts with platforms on rail. The scan visits rows from the bottom as the original does, but our RNG stream is not aligned with the original's, so individual draws are not comparable.
- Rail tiles are treated as zoneable so station platforms can be placed (the original must, since station footprints need weights on their rail tiles); ordinary footprints still reject rail.

**Measured** (free play, no roads, failure timer disabled, seeds 1–5, [report](../../docs/training/fidelity-aya-growth-2026-11-11/README.md)): houses inside a lot's one-tile ring fall from 4.2 and 8.6 per game (Los Angeles, t = 600/1200 s) and 1.2 and 4.2 (London) to 0; mean house-to-own-destination distance rises 6.6 → 8.4 and 9.4 → 10.7 tiles (Los Angeles) and 7.7 → 8.3 and 8.4 → 8.6 (London). Houses at 1200 s: 44.4 → 50.0 (Los Angeles), 34.0 → 37.8 (London).

**Open questions.** Stations now use the station layer (London's covers 85 tiles at weight 1). Beijing paints an "all colours" destination layer that the original never reads for a colour; the older zone export (`ShopZones`, still used by Custom) includes it. `isActive` and destination activation time are taken as "exists" and spawn time.


## 090 - House driveways, the path-away test and playable edges (11 November 2026, `fidelity-aya-growth`, merged into `fidelity-aya` as f12)

**Evidence.** House placement offers four layouts (driveway north, east, south, west), each its own placement with its own random draw; a driveway's target tile must lie inside the placeable area, be driveable and empty of buildings, not be rail, and the road node must be settable. The chosen placement must pass the original's path-away test: up to eight directions radiating from the driveway (forward, then ±45°, ±90°, ±135°, back), each probing five tiles out (up to five further if that tile holds a building) and asking a tile A* (8-neighbour, costs 70/99, octile heuristic, 300 iterations, buildable tiles only, the new footprint blocked) for a path; after five probes that reached a free tile without a path it gives up. The whole-tile playable area is [ceil(min), floor(max)] and `RectFixed.Contains` includes both edges; classic rules do not allow spawning at map edges, so placement uses the playable area inset by one tile on every side, and the driveway target must be inside the inset area too.

**Engineering choices.** Our previous code pointed a house's driveway at the destination that triggered it; it now comes from the placement. The path-away test follows the original's probe and A*; outside the data canvas counts as buildable and free, as the original's matrix default does; tie-breaking inside the open list may differ. The driveway-node test is approximated by our existing rules (no roundabout tile, no tile pending removal). `UpdatePlayableBounds` now includes the maximum column and the top row (original maximum y); stored bounds keep an exclusive maximum, so the observation fields `playableXMax`/`playableYMax` are one larger and `playableYMin` one smaller where not clipped. Custom (full canvas) and custom-scenario bounds are untouched.


## 091 - Spawn schedule: houses only from the supply test, 10 s between lots, double-lot and circle fallbacks (11 November 2026, `fidelity-aya-growth`, merged into `fidelity-aya` as f12)

**Evidence.** In the original a destination never brings a house: houses are scheduled only when a colour with no pending house has a destination with insufficient supply, at max(now, that colour's latest house spawn or schedule + 10 s), and a failed house retries 2 s later. After a new lot spawns, every later non-fixed destination entry is pushed to at least now + 10 s; joining a double lot does not push. A NoPreference entry rolls double/solo once (p = 0.3, +0.05 per solo roll, reset on a double) and keeps the result. A double-capable entry is offered only the first vacant double lot of its kind (station or not) and does not join it if that lot's destination has the same colour; it then places a new lot. A double entry that fails while its attempts exceed 4 becomes Solo for good with attempts 1 (a forced double instead hands its preference to the next entry of its colour; otherwise p += 0.05). A circle entry that fails while its attempts exceed 5 becomes a Normal destination of its colour (a random active colour for "any"), attempts reset.

**Engineering choices.** Pending houses are `ScheduledSpawn` entries of type 1 carrying their grouping; they are not listed in the `scheduledSpawns` observation (it keeps meaning "pending destination entries"). Reset runs the plan, the house schedule and the plan again at time 0, so the first house appears at reset rather than after the first tick (the protocol checks expect at least two buildings at reset). Failed entries still retry at now + delay (the original adds the delay to the entry's time; the two differ only when an entry is processed late). The old code's immediate supporting house, its discard of a destination without one, and its retry-forever circles are removed for OriginalReference.

**Measured.** Destinations at 1200 s: 11.0 → 11.4 (Los Angeles), 13.0 → 14.2 (London); circle upgrades at 1200 s: 2.2 → 3.0 and 1.4 → 0.8.


## 092 - Supply distance from the tile outside the driveway (11 November 2026, `fidelity-aya-growth`, merged into `fidelity-aya` as f12)

**Evidence.** The original's supply contribution measures the octile distance from the house tile to the lot's top-left driveway tile if it has one, else its bottom-right one; the carpark model defines these as the tile just outside the lot (the west/north entrance of a double lot). Ours used the entrance tile inside the lot.

**Engineering choice.** `HouseSupplyContribution` uses the tile outside the first entrance (`Entrances[0]`, the west/north one of a shared lot). It affects only house scheduling, i.e. free play.

**Checks for 085–088.** Simulator `2026-11-11.g1`: 92 suites pass (85 + 7 new placement suites in `OriginalPlacementChecks.cs`; no existing assertion changed); five-map and training-readiness checks pass; replay v21 is bit-identical to f7 (default run COMPLETED, 353 of 400 events, 663 trips, game over at 1214.8 s; 16 fixed phase sets mean 777.8, fitted phases 799 at 1307 s with 400 of 400 events).


## 093 - Motorway slots count as roads; who is circulating (11 November 2026, `fidelity-aya`)

**Evidence.** `RoadTileSignature.AddNode` adds a motorway's slot as a road node of its end tile, so lanes into that tile see one more outbound choice (`GetLaneSpeed` intersection factor), `GetNumberOfRoadsInIntersectionForSlowingVehicles` counts the slot's direction, and a tile with one road plus a motorway has no U-turn lane. `InboundVehicleDistanceComparer.IsVehicleOnRoundabout` counts a car as circulating only on a ring lane or a lane feeding one; ours also counted cars on a ring tile's exit lane.

**Engineering choice** (OriginalReference). `RoadDegree` (connections plus active motorway ends) in `OriginalLaneSpeed`, `RoadsForIntersectionSlowdown` and the `FindRoute` U-turn test; `OnTargetRoundabout` requires the car's lane to continue on the ring.

**Measured.** Simulator `2026-11-10.f13`: ablations showed the circulating change alone is neutral (784.5) and the U-turn test alone small; motorway slots in lane speeds and the slowdown lower the 16-phase mean 784.5 → 762.9 (584–803, the 584 run is a high-demand phase set with no stuck cars), 5/16 reach the end; fitted phases 784 at 1301 s → 795 at 1308 s. Kept for fidelity. 92 suites, five-map checks and training readiness pass.


## 094 - Roundabout placement as the original (11 November 2026, `fidelity-aya`)

**Evidence.** `AddRoundaboutEdit`: only ring-tile roads that cannot be exits, and the centre's links, are mothballed (their concrete returns on release); valid exits stay connected and stay spent; no links are created. `GameBehaviourModel` prices links to ring tiles like links to empty tiles (1 concrete). Ours unlinked and refunded every footprint link, then linked every neighbouring road in an allowed direction for free, and priced ring links at 0.

**Engineering choice** (OriginalReference). `AddRoundabout` keeps existing valid exits and makes no new links; `RoadConnectionCost` charges 1 for an outside–ring link (0 inside a roundabout). The roundabout concrete test now expects two held links for a straight road through the centre, with both exits still connected, and each original connection refunded exactly once after removal. The roundabout's own activation delay and the hot-swap hold are not modelled.

**Measured.** Simulator `2026-11-10.f14`: 16-phase mean 762.9 → 791.4 (763–804), 14/16 reach the end; fitted phases 807 at the end. All replay events still apply. The free links had been adding junction links the original never had. 92 suites, five-map checks and training readiness pass.


## 095 - Return paths after an erase; erasable ring exits (11 November 2026, `fidelity-aya`)

**Evidence.** After any lane change the original flags every car whose committed lanes can reach a changed lane and re-paths it in the next pathfinding step, forward and return paths alike (`LaneUpdateProcess`, `VehiclePathfindingProcess`); a mothballed lane's concrete returns once no car has it in a forward or return path. Ours refreshed a stored return route only for whole-tile removals, so an erased link stayed held by cars parked or driving out until they left their bay. The original's eraser clears an exit into a ring tile like any road; ours refused any link touching a roundabout.

**Engineering choice** (OriginalReference). `RemoveRoadConnection` re-routes the stored `ReturnRoute` of non-returning cars that used the erased link, keeping the old one when no alternative exists; only links inside a roundabout need the circle tool.

**Measured.** Simulator `2026-11-10.f15`: 16-phase mean 791.4 → 788.3 (735–805), 13/16 reach the end; fitted phases 808 at the end. 92 suites, five-map checks and training readiness pass.


## 096 - Optional scheduled time for late destinations in replays (11 November 2026, `fidelity-aya`)

**Evidence.** The original adds extra demand to a colour while one of its scheduled destinations is waiting for a placement (`GenerateDemandProcess.BalanceDemandFromFailedSpawns`, retries every `FailedDestinationRetryDelay` 20 s). Recorded replays force spawns and disable growth, so this demand was always zero, although the plan's schedule formula proves two red destinations in replay v21 arrived at least 69 s and 108 s after they were scheduled. The video at ~1260 s shows red overcrowding that our replay does not reproduce.

**Engineering choice.** Custom-scenario destination events accept an optional `scheduledAt`; between it and the event the session keeps a delayed plan entry for the colour (one attempt per 20 s), feeding the simulator's existing extra-demand rule. Scenarios without the field behave exactly as before (no version bump). Replay v21 stays the benchmark; `docs/training/fidelity-aya-2026-11-10/replay-candidate-v21a.json` carries the two lower-bound annotations.

**Measured.** On `2026-11-10.f15`: v21a 16-phase mean 774.2 (630–815), median 796.5, 9/16 reach the end; fitted phases 815 at the end (v21: 788.3, fitted 808). 92 suites pass.


## 097 - Tile-corner lanes on diagonal steps (11 November 2026, `fidelity-aya`)

**Evidence.** `LaneUpdateProcess`/`TileCornerModel`: a diagonal link between two tiles passes through a corner chunk; each tile chunk's lane ends 0.5 tiles (one world unit) from its centre and the corner chunk's lane covers the rest (√2 − 1 tiles). A corner chunk with two lanes is never arbitrated (`lanes.Count <= 2`). By `GetLaneSpeed`, the tile lane before the corner has one outbound lane and takes only its turn factor, while the corner lane takes the intersection factor when the next tile branches. Ours ran each tile lane to the shared corner point, so the whole approach took the 0.5 factor, diagonal junction legs were ~0.2 tiles longer, and commitment reached further up diagonal approaches.

**Engineering choice** (OriginalReference; not on roundabout, motorway or carpark-transit steps). `MakeLanes` trims diagonal tile lanes and inserts `CornerLane` (`IsCorner`, keyed by tile and direction); corner lanes are skipped by chunk arbitration, the traversing check and `Conflicts`. Crossing diagonals (a four-lane corner) remain unsupported. New fidelity check: alternating tile/corner lanes, corner length √2 − 1, continuity.

**Measured.** Simulator `2026-11-10.f16`: 16-phase mean 788.3 → 791.1 (740–809), 13/16 reach the end; fitted phases 808 → 791, failing at 1310 s (original ~1314 s). 93 suites, five-map checks and training readiness pass.


## 098 - Bridge crossings as the original's passages (11 November 2026, `fidelity-aya`)

**Evidence.** `Passage.WillConnectionStartPassage`: a link from an unobstructed tile onto an obstructed (water) tile with no roads starts a passage, consuming one bridge (`AddRoadEdit.ApplyToUpgradeDatabase`); links along water extend it for free; `WillConnectionJoinPassages` (both water tiles already carrying roads) mothballs and releases one bridge, so joining two crossings returns one; stock returns when a mothballed crossing releases. Ours grouped bridge tiles into spans by orthogonal adjacency, so parallel bridges shared one bridge, and a bridge tile emptied by connection erases was never cleared or refunded.

**Engineering choice** (OriginalReference). `DrawRoad` and the reference builder pass the stroke's previous cell to the bridge build: from a bridge tile it joins that crossing, otherwise it starts one; `Connect` merges two crossings and refunds one bridge; connection retirement clears an unconnected bridge tile and refunds the crossing when its last tile goes. The direct bridge-tile tool (no stroke) keeps the adjacency grouping. Water-tile junction limits are not modelled. New check: two parallel strokes use two bridges, linking them returns one.

**Measured.** Simulator `2026-11-10.f17`: replay v21 unchanged (791.1; no parallel bridges in it). 93 suites, five-map checks and training readiness pass.


## 099 - Stroke details: unaffordable links and strokes into houses (11 November 2026, `fidelity-aya`)

**Evidence.** `DrawRoadAction` keeps stepping when concrete runs out, so later free or mothballed links in the same stroke are still made; `TileEditor` turns a house's driveway toward a stroke that enters or passes through the house. Ours abandoned the rest of the stroke at the first unaffordable link and realigned a driveway only when the stroke started at the house.

**Engineering choice** (OriginalReference). `DrawRoad` skips the unaffordable link and continues; a stroke reaching a house from a side other than its driveway realigns the driveway first. Drawing remains a rounded raster line rather than the original's greedy eight-direction stepping. New check: a stroke into an east-facing house from the south turns its driveway south and links it.

**Measured.** Simulator `2026-11-10.f18`: replay v21 unchanged (791.1). 94 suites, five-map checks and training readiness pass.


## 100 - Traffic-light placement needs a junction (11 November 2026, `fidelity-aya`)

**Evidence.** `TileEditor` allows a traffic light only on a tile with at least three roads (live or pending, motorway ramps included), no active ramp and no rail. Ours accepted any ordinary road tile (motorway ends excepted).

**Engineering choice** (OriginalReference). `Build(TrafficLight)` refuses tiles with fewer than three connections or with rail. Our roads become active at once, so "pending" needs no separate count here; automatic removal of a light whose tile later drops below three roads stays unadopted (decision 085).

**Measured.** Simulator `2026-11-10.f19`: both replay lights qualify; replay v21 unchanged (791.1). 94 suites, five-map checks and training readiness pass.


## 101 - Full-lot drive-through across the nearest bay (11 November 2026, `fidelity-aya`)

**Evidence.** `ParkVehiclesProcess`: with no free bay the car becomes `DrivingHome` and `VehiclePathfindingProcess` paths from its committed lane to its house over every lane; bay lanes are ordinary graph edges (carpark lanes at double cost), so the cheapest way out crosses the bay nearest the entrance (`CarparkModel`: outer bay entry → bay lane → inner bay exit). The parked car sits at the middle of that bay lane, so the drive-through follows it. Ours drove a full lap of the lot and could not see parked cars.

**Engineering choice** (OriginalReference). `ParkingDriveThrough` returns the nearest bay's entry and exit routes back to back (delivery still on leaving the entrance lane); the leader search treats a parked car as a stopped leader at the end of its `bay-park` lane for any car whose path crosses that bay.

**Measured.** Simulator `2026-11-10.f20`: no lot fills in replay v21 (no drive-through time), so the replay is unchanged (791.1); the drive-through check and the carpark separation fixtures pass. 94 suites, five-map checks and training readiness pass.


## 102 - Replay v21b: late destinations from circle conversion; plausible demand phases (11 November 2026, `fidelity-aya`)

**Evidence.** In the LA plan, items with grouping 3 are circles (upgrades). `BuildingSpawningProcess`: a circle with no eligible destination retries every 20 s (`FailedDestinationRetryDelay`), becomes an ordinary destination of its colour at the attempt after its sixth failure, and is placed at the next retry. That is at least 140 s after it was scheduled, and its colour gets `BalanceDemandFromFailedSpawns` extra demand the whole time. The recording shows no upgrade before 1030 s, but the plan schedules a yellow circle (chunk days 16–36) and a red circle (chunk days 30–42). The slot bounds identify yellow 26,18 (652 s) and red 12,19 (919 s) as those converted circles, scheduled by 512 s and 779 s, and show red 30,18 (662 s) on time.

**Engineering choice** (replay data, not a rule change). `replay-candidate-v21b.json` = v21a with `scheduledAt` 512 s on yellow 26,18 and 779 s on red 12,19, plus 405 s on red 17,17 as before. These are latest possible times, so lower-bound delays. With this demand, the five demand phases refitted to the real score curve fit far better: RMSE 3.9 instead of 8.7 trips, with a positive delivery lag. The 20 independent fits become the phase sets for judging the replay, in place of random phases that contradict the real curve.

**Measured.** Simulator `2026-11-10.f20` on the 20 plausible phase sets: v21b mean 791.5 (744–824), 4/20 reach the end, mean end 1297 s; v21 784.8 (743–801). The original scored 835 and ended at about 1314.6 s. Pin creation matches the original formula within one pin, so the remaining gap is time from dispatch to delivery and late congestion at the red lots. Report: `docs/training/fidelity-aya-2026-11-10/README.md`, section "Replay v21b".


## 103 - Bridges carry no junctions (11 November 2026, `fidelity-aya`)

**Evidence.** `TileEditor.WouldConnectionPassPassageConstraints` (bridges over water): a link touching a water tile is refused if that tile already has more than one live or pending road. Live includes erased roads still in use. A link is also refused from a water tile with no road, and a link that restores an erased (mothballed) road is always allowed. Diagonals that would cross at a tile corner over water are refused; ours already refuses crossing diagonals on every tile. Ours allowed any number of roads on a bridge tile and strokes starting on bare water.

**Engineering choice** (OriginalReference). `Connect` refuses such links. The stroke loop skips building a bridge tile for a refused link, so no bridge is spent on a road that cannot form. The two bridge-stock checks now use legal moves: the span is drawn from land, and two crossings are merged by linking their dead-end ends instead of their middles. A new check covers both refusals.

**Measured.** Simulator `2026-11-10.f21`: replay v21b on the 20 plausible phase sets is identical to f20 (791.5; the replay's bridges have no junctions). 94 suites pass.


## 104 - Motorway ramps take a free side and keep it (11 November 2026, `fidelity-aya`)

**Evidence.** `AddMotorwayAction.SetDanglingTile`: the free ramp directions of each end tile are those where `CanSetNodeState` accepts a motorway node, meaning no road or other ramp on that side. Every pair (start ramp a, end ramp b) is scored (a·n/2+1/2)(b·(−n)/2+1/2), with n the unit vector from start to end, plus 0.1 when a and b lie on the same side of the line, and the best pair wins; ties go to the first in enumeration order N, NE, E, SE, S, SW, W, NW. In an edit, the kept end keeps its ramp when that ramp is within one step of the closest direction and within 45° of the new line. The ramp is stored on the motorway, and `Tile.CanSetNodeState` refuses any road node on a side that holds a live or planned motorway. Ours recomputed the closest direction whenever lanes were rebuilt, ignored roads already on that side, and let roads use the ramp's side.

**Engineering choice** (OriginalReference). `MotorwayState` stores `StartDirection` and `EndDirection`, chosen as above when the motorway is created or edited. Motorway lanes use the stored directions, and `Connect` refuses a road link on a ramp's side. The rail-diagonal penalty (−0.5 for a diagonal ramp between two rail tiles) is not modelled. For a new motorway, the anchor ramp's dependence on the mouse drag is also omitted. Replay v21 records two strokes into new motorway ends in the same video second as, and after, the motorway; under this rule they are refused, so v21c/v21r swap those two pairs (README, "Replay v21c and v21r").

**Measured.** Simulator `2026-11-10.f22`: v21c on the 20 plausible phase sets 801.4 (755–831), 6/20 reach the end (f21 791.5, 4/20; paired +9.9, range −62 to +63). v21r on the 16 random sets 784.0 (626–805; f21 791.1), fitted 802 reaching the end (f21 791 failing at 1310 s). 95 suites pass (new: ramps take a free side and block it).


## 106 - Crossing diagonals form a corner junction (11 November 2026, `fidelity-aya`)

Numbered 106 because upstream `main` already uses 105 (upstream's 042, renumbered in the merge of 11 November).

**Evidence.** `TileEditor.WouldConnectionPassPassageConstraints` refuses a diagonal that would cross another at a tile corner only when the new link starts or ends over an obstruction (water, mountain). On land the crossing is allowed. `LaneUpdateProcess` then builds a `TileCornerModel` whose signature has the four diagonal nodes. `RoadTileSignature.AddNode` connects every pair of nodes except a U-turn, so the corner is a junction: cars cross, and can also turn onto the other diagonal. `GetLaneSpeed` gives the intersection factor to a lane with more than one onward lane, so a tile lane leading into the crossing corner slows. Corner chunks are separate road chunks, never controlled by a light. Ours refused every crossing stroke, and its corner lanes were treated as part of the tile they leave: they could take that tile's light state and junction slowdown.

**Engineering choice** (OriginalReference). `Connect` accepts a crossing diagonal unless the new link touches water or a roundabout end (roundabout corners are not modelled). Lanes carry a chunk cell (`Lane.ChunkCell`): the tile for ordinary lanes, a corner code with negative coordinates for corner lanes. Arbitration, conflict tests, light checks and the intersection slowdown compare chunks instead of tiles. A crossing corner arbitrates like any junction with more than two lanes, using the existing connection-intersection rule with the diagonal node directions. Our routes list cells, so a turn at the corner is an orthogonal step between two tiles that have no direct link (`CornerTurn`). Its lanes are the tile lane toward the corner, a turning corner lane, and the next tile's lane, as if arriving along the other diagonal. Where the two tiles are also linked directly the direct link is used, and with crossings on both sides of their edge the first side is used. The route cost of a turn is half a diagonal at the tile's lane speed plus half at turn speed. A route step through a turn counts as using both diagonals for erase-and-release.

**Measured.** Simulator `2026-11-10.f23`. Replay v21c on the 60 plausible phase sets scores 796.3 (669–829), with 18/60 reaching the end. f22 scored 794.4 with 15/60, a paired +2.0 ± 2.0. The replay has no crossings, so the change comes from corner lanes arbitrating as their own chunk. A new check covers the build rules, the shared corner chunk, the conflict between crossing lanes, routes straight through and turning, and a flow scenario: 12 deliveries over both diagonals with a turn, with crossing lanes never occupied together. 96 suites pass.


## 107 - Blocking cycles start from stuck vehicles; all-leader cycles push (12 November 2026, `fidelity-aya`)

**Evidence.** `VehicleMovementProcess` adds a vehicle to its stuck list in two cases: it is refused entry to the chunk of its next lane (`path[0]`) with no leader on its own lane, or its nearest obstacle is a leader whose position is less than `MinimumGap` (0.1 world units) ahead while its next speed is below `minSpeedBeforePushingCycle` (0.2 world units/s). The distance is a position difference, so in the second case the two cars practically overlap (lane merges). From each stuck vehicle it follows `blockingVehicle`: the leader at any distance, or the vehicle refusing its next-lane entry; a junction further ahead sets no blocking vehicle. A chain that closes on itself is a cycle (`BreakCycle`). Members refused at a junction shove; if every member follows a leader, each pushes into its leader: it takes the leader's speed as at least 0.2 world units/s and the gap as at least a vehicle length plus two minimum gaps. The push ends when the leader moves faster on its own or the car's obstacle changes. Ours searched every chain made of junction refusals and tight, slow leaders, from any car, and left all-leader cycles alone.

**Engineering choice** (OriginalReference). `MarkBlockingCycles` follows the original. `Vehicle.PushingInto` holds a push, and a pushing car may close in on its leader past the usual clearance. The adjacent-junction gridlock check now registers its fixture cars as dispatch would. It still clears by shoving, because two of its cars are refused at their next chunk.

**Measured.** Replay v21c on the 60 plausible phase sets: 801.8 (732–839), against f23's 796.3 (669–829). Paired +5.5 ± 3.5 at the end, +0.4 to +1.0 trips at 900–1200 s ([data](../../docs/training/fidelity-aya-2026-11-10/measurements/bench-f24-replay-v21c-p60.txt)).


## 108 - A new roundabout stays planned until the lanes it replaces clear (12 November 2026, `fidelity-aya`)

**Evidence.** `AddRoundaboutEdit` puts the circle in the Planned state and mothballs the roads it replaces at once. Planned connections have no lanes. `ReleaseMothballedLanesProcess.CanPlannedRoundaboutHotswap` activates the circle in the first step in which every replaced lane, and every lane leading into or out of one, satisfies `LaneModel.CanHotswap`: no vehicle on it, and none committed to it (committed means within the next two lanes of a path). Meanwhile those lanes are `IsAboutToHotswap`. A car whose `path[0]` and `path[1]` are not about to hot-swap but whose `path[2]` is stops at the end of its current lane (`VehicleMovementProcess`, not from a carpark lane). Mothballed lanes cost 100000 in pathfinding and dispatch does not use them. Ours activated the circle at once, so cars still on the old junction drove through the new ring.

**Engineering choice** (OriginalReference, `RoundaboutActivation.cs`).
- `RoundaboutState.Planned` holds the circle back. New routes do not pass through its five tiles; a route with no other way keeps its old lanes.
- Cars still on replaced lanes arbitrate with the old junction's road counts.
- The hot-swap stop is applied as in the original.
- The circle activates in the step after no car has a replaced lane among its current lane and next two. With no such car it activates at once (the original does so in the next step).
- A stored way home through a planned circle is re-found when the car sets off home.
- With several circles planned at once, one held circle holds all of them.

**Measured.** Replay v21c, 60 sets: f24 (decisions 107–109) 796.0 (737–836), 16/60 reach the end. Decision 108 alone costs 5.8 ± 2.6 at the end against decision 107. The difference starts after the replay's only roundabout (19,9 at 1051 s): −1.2 trips by 1100 s. In the recording, a car crosses the old centre about a second after the circle is placed, which this model allows. The video does not show whether the circle was drawn as planned. A check covers a circle placed under traffic: it stays planned, no route passes through it, it activates once the old lanes clear, and every trip is delivered.


## 109 - Cars at train crossings; tile-corner stopping points (12 November 2026, `fidelity-aya`)

**Evidence.**
- Constants (`SimulationConstantsData`): `maxAccelerationOnCrossings` 0.2, `targetSpeedTowardsCrossings` 0.5, `decelerationExponentTowardsCrossings` 1, `crossingSlowDistance` 3, `crossingStopDistance` 1.8.
- On or just before a crossing chunk, the acceleration limit is `maxAccelerationOnCrossings`. With no other obstacle, a car more than `crossingSlowDistance` vehicle lengths from a crossing slows towards half its desired speed. The intersection slowdown takes precedence.
- `RoadChunkModel.CanInboundVehicleEnter` runs the crossing tests before all others, unless the car is already on an open crossing. A closed crossing refuses entry, except at a tile-corner crossing less than one vehicle length ahead. An open crossing refuses entry while a car on a conflicting lane of a chunk along the path is stopped or within three vehicle lengths of the vehicle blocking it. The scan starts at the next lane and ends after the first chunk that is not a crossing.
- A crossing further ahead than the next lane is approached `crossingStopDistance` vehicle lengths shorter. Tile-corner chunks take no `IntersectionStoppingOffset`, either for stopping or for the intersection slowdown.
- `LaneUpdateProcess` makes a crossing at a tile corner where a diagonal road passes between the two tiles of a diagonal rail step.
- Ours only refused closed crossings on rail tiles.

**Engineering choice** (OriginalReference). The rules above are ported. A corner crossing closes when either rail tile is closed. The congestion test uses the previous tick's obstacles. Chunks with two lanes or fewer have no traversing list in the original, so they are not scanned. Two smaller changes: `ConnectionsIntersect` takes the original's `smallIntersection` argument (on for arbitration, off for the crossing test), and `Vehicle.BlockingVehicle` records the original's blocking vehicle. Crossing signal timing is unchanged; it already follows the train's blocked section and the 2 s reopening wait.

**Measured.** The LA replay builds no road over its rail line (0 road tiles on rail at the end), so it is unchanged (f24 equals the run with only decisions 107 and 108). A new check: a car slows before an open crossing (entry speed 1.09 against 1.39 tiles/s cruising) and never accelerates above 0.1 tiles/s² on it. 98 suites pass.


## 110 - Replay v21d: event times read from the game's clock (12 November 2026, `fidelity-aya`)

**Evidence.**
- `ClockView` draws the hand at 12 o'clock at t = 0 and turns it 36 degrees per game second, so one turn is 10 s.
- `IsDayTime` (hours 6 to 18) gives the light face and the night gives the dark face, so midnight is 12 o'clock on the dark face. Day 0 is Monday and a week is 140 s.
- So every frame of the recording that shows the dial gives the game time within the day.
- The weekly upgrade screen opens at or just after Monday 00:00. In week 4 the clock ran on for about 5 s because the player was still acting.
- Read at 4 frames per second and anchored week by week, the dial puts each week's start and end in agreement exactly, with no day lost.
- Against it, replay v21c is within about 1 s for most of the game. Through weeks 4 and 5 (video 241 to 365 s, game 433 to 677 s), v21c converted video time slightly too slowly, so its events there are 2 to 5 s early. Events made during a pause belong at the paused clock time (678.8 s, not 677).

**Engineering choice** (replay data, not a rule change). `replay-candidate-v21d.json` = v21c with each player action and spawn timed by the dial ([source](../../docs/training/fidelity-aya-2026-11-10/source/week_dial.py), [make_v21d.py](../../docs/training/fidelity-aya-2026-11-10/source/make_v21d.py)):
- Offers stay on the week boundaries.
- Events in unreadable stretches take their neighbours' correction, or the paused time inside a pause.
- The two converted circles keep the rule "scheduled at least 140 s before they appear", from their re-read appearance times.

The real score curve is re-timed the same way, and the 60 demand-phase sets are refitted to it. All 60 fits improve, with error 3.58 to 3.7 trips instead of 3.86 to 3.9. The benchmark becomes v21d on these 60 sets.

**Measured.** Simulator f24 on the 60 refitted sets: 805.5 (759 to 833, median 811.5), 22/60 reach the end, mean end 1302 s. On the old sets: v21c 796.0, v21d 805.1 (paired +9.1 +/- 3.5). The original scored 835 and ended at about 1314.6 s.


## 111 - The original re-plan is switched on (12 November 2026, `fidelity-aya`)

**Evidence.** The port of `VehiclePathfindingProcess` (current lane plus two kept, `RefreshJourneyOriginal`, 11 November) matches the original's code. It was off because it lowered replay v21c by about 11 trips. On replay v21d (decision 110) with the refitted phases it changes f24 by -1.9 +/- 3.2 (median +0.5, 30/60 better), under one trip at any time up to 1200 s. The earlier loss came from the replay's timing errors.

**Engineering choice** (OriginalReference). `OriginalRepath = true`. Stored ways home are re-found when the car sets off home.

**Measured.** See decision 113.


## 112 - Junction exit space: a leader on the entered chunk counts the lane length less one vehicle length (12 November 2026, `fidelity-aya`)

**Evidence.** `RoadChunkModel.DoesVehicleHaveSpace` follows the entering car's obstacle chain for up to five vehicles. For a leading vehicle on a lane of the chunk being entered, it takes `lane.Length - VehicleLength` off the distance to that leader, wherever on the lane the leader is, and then adds `max(distance - VehicleLength, 0)`. In effect the junction lane itself offers no space: the car may enter beside a same-exit car only if more than two vehicle lengths are free beyond the junction, or the leader in the junction has no obstacle. Ours, built from the earlier rule description, took off only the part of the lane ahead of the leader, which credits the leader's progress through the junction.

**Engineering choice** (OriginalReference). `HasExitSpace` uses the original formula.

**Measured.** On f24 alone: -16.6 +/- 3.2 at the end, -2.2 trips by 1100 s, -4.0 by 1200 s. Nothing changes before 1000 s; the rule bites only when traffic queues beyond a junction. It moves the replay away from the real game; it is kept because it is the original's code.


## 113 - Inbound registrations are stamped with the lane's position in the path (12 November 2026, `fidelity-aya`)

**Evidence.** `AssignPath` registers each new path lane with `AddInboundVehicle(vehicle, lane, path.Count)`, whose timestamp is the game time plus that offset: 1 for the next lane, 2 for the one after, and so on. The stamp breaks ties between candidates at the same distance. Ours added the route's total lane count to every registration.

**Engineering choice** (OriginalReference). `RegisterRoute` stamps time plus the lane's position after the current lane. Kept registrations keep their stamps.

**Measured.** Simulator `2026-11-10.f25` (decisions 111 to 113), replay v21d on the 60 refitted phase sets: 783.4 (684 to 832), 8/60 reach the end, mean end 1292 s. f24 scored 805.5 (paired -22.1 +/- 4.0). Without decision 113: 782.1 (decision 113 adds +1.3 +/- 4.2). Up to 1000 s, f25 is within one trip of f24 ([data](../../docs/training/fidelity-aya-2026-11-10/measurements/bench-f25-replay-v21d.txt)). 98 suites, five-map checks and training readiness pass.


## 114 - Traffic-light details from the decompiled code (12 November 2026, `fidelity-aya`)

**Evidence.** `TrafficLightModel` and `TrafficLightAlternatingProcess` were compared with our implementation, which had been written from a rule description. Matching: green pairs (opposites from north first, then three-step pairs clockwise before counter-clockwise, then singles); green 3 s, overtime 1 s, amber 0.7 s; the nearby guard (fewer than 3 cars within 1 world unit keeps the pair); the pair weight (committed cars only; squared waiting time over 30 s times multiplier 1; x4 on a mothballed lane; x0.1 for non-crossing turns until the first crossing car; x10 from a carpark lane; +1; x0.1 for a car blocked in the chunk on the current pair); strict-greater choice. Three details differed:
- The candidate order is the chunk's sorted inbound list: eligible entries by distance, then the rest. It decides where the nearby count stops at a blocked car and which cars get the non-crossing discount. Ours used registration order.
- The mothballed factor applies to a chosen lane whose connection was erased. Ours tested tile removal.
- After amber with no weighted pair, the current pair stays while the chunk has any inbound vehicle, committed or not. Ours required a committed one.

**Engineering choice** (OriginalReference). All three are ported. Eligibility ignores the traversing-collision part when ordering, and the blocked tests ignore the hot-swap obstacle.

**Measured.** Replay v21d, 60 refitted sets: 773.5 against f25's 783.4. The median paired difference is +0.5, but one run tips into overcrowding at the far red lot at 1080 s (-295; no gridlock, red cars all busy). The mean is -9.9 +/- 6.9 ([data](../../docs/training/fidelity-aya-2026-11-10/measurements/bench-f26-replay-v21d.txt)).


## 115 - Weekly upgrade offers drawn as the original draws them (12 November 2026, `fidelity-aya`)

**Evidence.** `GameBehaviourModel.GenerateNextUpgradeChoices` computes the package weights and their total once. Each pick draws against that total and walks the remaining packages against the original weight positions; the picked package leaves the list but its weight does not. If the draw is not used up, the last package is taken. Afterwards `OnUpgradeNotPresented` runs for every package left, so a type with two packages left counts twice, and then `OnUpgradePresented` resets the presented types. When nothing is eligible the week grants an empty concrete package. Ours sampled correctly without replacement, counted per type, and offered 20 concrete when nothing was eligible.

**Engineering choice** (OriginalReference, free play). Ported. Recorded replays keep their recorded offers, so the benchmark is unaffected.

**Measured.** 98 suites, five-map checks and training readiness pass on `2026-11-10.f26`.

