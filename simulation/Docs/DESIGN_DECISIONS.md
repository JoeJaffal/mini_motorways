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


## 042 - Selective playground updates from mohammad (29 October 2026)

User decision: copy only AI replay playback and retiring-road display fixes to
main, without merging training work. Engineering choice: port the replay core,
viewer, retiring-link display helper and three focused shared check suites from
mohammad f632008 onto main f02fe0e. Replay uses normal materials/actions and
blocks manual editing while active. Retiring pavement is display only. Existing
traffic physics and gameplay rules are unchanged. Training diagnostics, headless
training extensions, rewards, checkpoints and reports are excluded. Earlier
training chronology remains on mohammad in training/EXPERIMENT_HISTORY.md.
Validation results are recorded below; this is not evidence of game fidelity.

Validation: .NET 8 shared self-test passed all 40 suites (including replay
reproduction/tamper detection, helper/version rejection and retiring pavement
lifecycle/non-mutation). Five-map protocol verification passed 10 runs across
OriginalReference and Custom. `git diff --check` passed. Unity editor compilation
was also requested; its result is recorded below. No long training was run.
Unity 6000.6.0f1 batch import/compilation completed successfully, exit code 0,
with no C# compiler errors. No player build or interactive visual inspection was
performed in this port. The local-only editor log is
C:/Users/moham/mini_motorways/tmp/playground-main-unity.log.
