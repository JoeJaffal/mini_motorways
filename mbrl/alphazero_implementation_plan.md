# AlphaZero-Style Traffic Management — Implementation Plan

## 1. Agreed design

We will implement a **single-agent AlphaZero-style reinforcement-learning agent** for a **headless Unity traffic simulation**. The agent receives **structured simulator observations** (no screenshots or computer vision), uses a **policy/value neural network** and **Monte Carlo Tree Search (MCTS)** to evaluate future infrastructure decisions, and trains from simulated episodes.

The first version retains the **existing Python environment wrapper**: each policy action is followed by a separate `step` request of **20 ticks**, normally equal to **one simulated second** (0.05 seconds per tick). This is a wrapper design, **not** a restriction of the Unity simulator. We will benchmark the working implementation before optimizing its computational performance.

## 2. Simulator interface and execution

- The headless host accepts **one JSON object per line**, with **case-sensitive** command names.
- Coordinates are integer cells on a **50 × 30 grid**. `x,y` identifies the first cell; `toX,toY` identifies the second.
- **Construction and other gameplay commands do not advance simulation time**; only `step` does.
- Game-action responses provide `accepted`, `message`, `tripsDelta`, `spendingDelta`, `terminated`, `truncated`, and `observation`. Invalid requests or exceptions can return an `error` object.
- `message` is not a reliable indicator of the most recent command's outcome because it may be stale; use the structured response and resulting observation.

### Gameplay commands to support in candidate generation

| Command | Relevant behavior |
|---|---|
| `build` | Places one tile; tools include `Road`, `Bridge`, `Roundabout`, `TrafficLight`, and `Remove`. |
| `connect` | Connects two distinct neighboring traversable cells, including diagonals; creates no road tile. Adjacent roads are not necessarily linked. |
| `draw` | Rasterizes a straight line between endpoints, attempts missing road/bridge construction, and connects successive cells. **No fixed five-step limit**. It may partially succeed. |
| `driveway` | Changes a selected house's driveway direction using its observed building ID. |
| `motorway` | Places a motorway between eligible endpoints in `OriginalReference`. |
| `editMotorway` | Modifies an active motorway using its observed ID; successful changes can create a new ID. |
| `removeMotorway` | Retires an active motorway; stock return can be delayed. |
| `upgrade` | Selects an available zero-based `observation.upgradeChoices` index when an offer exists. |
| `step` | Advances traffic. In the current Python wrapper this is normally called automatically after the policy action. |

`reset` initializes an episode; `observe` retrieves the current observation. `reference` is a debug command, and `quit` exits the host. They are not proposed as normal policy actions.

The existing Python candidate generator currently proposes only **`wait`, `draw`, `motorway`, and `upgrade`**. `wait` is a **Python wrapper action**, not a headless simulator command. We will expand candidate generation to cover the available gameplay action categories instead of treating the current restricted set as the simulator's full action space.

## 3. Environment adapter and MCTS branching

Implement an environment adapter that:

1. Resets the Unity simulation and obtains structured observations.
2. Executes an agent-selected gameplay action through the wrapper.
3. Advances time by **20 ticks** after that action, preserving the current wrapper behavior; `wait` advances time without a preceding construction action.
4. Reads the resulting observation, reward components, and termination information.
5. Supports independent hypothetical transitions for MCTS.

**Branching strategy:** keep the branching implementation replaceable. Prefer **snapshot/restore** if supported and efficient; otherwise start with **reset-and-replay**, provided seeded replay is verified to be deterministic. Once the initial code works, benchmark the alternatives rather than assuming which is cheaper in this implementation.

The branching mechanism must reproduce the state relevant to later traffic evolution, including infrastructure, vehicles, inventory, pending removals, simulation time, and random state. Search must not reveal the actual unknown future traffic of an evaluation episode.

## 4. State representation and neural network

Use the simulator's **structured state**, not images. The intended representation combines:

- **Grid/spatial information:** 50 × 30 terrain, water, obstacles, building positions, infrastructure, and traffic features.
- **Actual network connectivity:** traversable links, building entrances/driveways, intersections, and motorway edges. **Grid adjacency alone is insufficient**, because neighboring roads need not be linked.
- **Global information:** available inventory/resources, upgrade choices, and simulation time.

The proposed long-term architecture is a **hybrid grid-and-graph encoder**. For the initial working version, a **CNN/grid encoder with explicit connectivity features** is an acceptable simplification; a GNN can be evaluated later if needed. Features dependent on simulator observations must be checked against fields actually exposed by `observation`.

The shared encoder feeds two heads:

- **Policy head:** \(p_\theta(a\mid s)\), scores the **generated legal candidate actions** (a variable-size set).
- **Value head:** \(V_\theta(s)\), estimates expected future cumulative reward.

## 5. Candidate-action generator

The action generator must **consider every relevant gameplay command category**, while generating a manageable set of **valid, strategically relevant** candidates rather than every possible parameter combination.

- Produce route-based **`draw`** candidates and local **`build`** / **`connect`** candidates.
- Include feasible **driveway changes**, **motorway placement/edit/removal**, **construction removal**, and **weekly upgrades** when applicable.
- Include the Python wrapper's **`wait`** action.
- Apply the simulator's geometry, connectivity, inventory, and command-specific constraints.
- Consider multiple route alternatives rather than returning only one mandatory stroke.
- Interpret a `draw` that partially succeeds using the **actual returned observation and changes**, not the requested line as though fully built.
- Handle delayed removals/stock refunds and changing motorway IDs from the resulting observation.

The generator determines which candidates can be considered; the **policy network ranks them** and **MCTS searches their consequences**. Candidate count/selection can be tuned after the first implementation.

## 6. Reward definition

The agreed general objective is:

\[
r_t=c_t-\alpha w_t-\beta g_t-\lambda m_t
\]

For the **initial experiment**, set **\(\beta=0\)**:

\[
\boxed{r_t=c_t-\alpha w_t-\lambda m_t}
\]

| Term | Initial meaning |
|---|---|
| \(c_t\) | **Incremental completed trips** during the agent transition; coefficient fixed at **1**. |
| \(w_t\) | Vehicle waiting time accumulated during the wrapper's simulation interval. |
| \(m_t\) | Infrastructure modification cost attributable to the action, under a consistent accounting definition. |
| \(\alpha\) | Waiting-time penalty coefficient, initially calibrated and later tuned. |
| \(\lambda\) | Infrastructure-cost penalty coefficient, initially calibrated and later tuned. |
| \(g_t\), \(\beta\) | Congestion metric and coefficient; monitor congestion in evaluation, but initially set \(\beta=0\). |

For the first implementation:

1. Collect preliminary baseline measurements to establish **fixed reference scales** for waiting and infrastructure cost.
2. Choose interpretable initial values for \(\alpha\) and \(\lambda\); **do not treat illustrative values as finalized coefficients**.
3. Calculate reward over each **complete wrapper transition** (policy action plus time advance), without double-counting trips.
4. Check what `spendingDelta` actually measures before relying on it for \(m_t\). Stock refunds and motorway edits mean inventory changes may not equal modification cost.
5. Keep a consistent infrastructure/resource budget across agents.

After the baseline experiment, tune the penalty coefficients on validation scenarios. Compare the initial reward with an experiment that reintroduces congestion (\(\beta>0\)) to determine whether that term improves performance or redundantly penalizes waiting.

## 7. AlphaZero-style MCTS

At each wrapper decision:

1. Read the current structured observation.
2. Generate the valid candidate actions.
3. Obtain policy priors and a state-value estimate from the neural network.
4. Run **single-agent MCTS** using independent hypothetical Unity transitions. A typical selection rule is PUCT, balancing estimated action value, policy prior, and search visits.
5. Use search visit counts to form an improved action distribution.
6. Execute the selected action in the actual wrapper environment, then advance **20 ticks**.

MCTS must account for stochastic traffic outcomes rather than assuming that one sampled future is guaranteed. Its backup rules must be appropriate for **single-agent cumulative reward**, not two-player sign-alternating chess returns.

We will choose the number of MCTS simulations and other search parameters based on experiments after the first working version.

## 8. Training objective

We agreed on the standard **policy + value + regularization** objective; there is **no learned dynamics/reward-prediction network** in this AlphaZero-style approach because MCTS uses the Unity simulator.

\[
\boxed{
\mathcal L(\theta)
=\eta_p\mathcal L_{\mathrm{policy}}
+\eta_v\mathcal L_{\mathrm{value}}
+\eta_{\mathrm{reg}}\lVert\theta\rVert_2^2
}
\]

Policy loss, using MCTS visit-count distribution \(\pi_t\):

\[
\mathcal L_{\mathrm{policy}}
=-\sum_{a\in A(s_t)}\pi_t(a)\log p_\theta(a\mid s_t)
\]

Value loss, using an observed discounted return \(z_t\) from a Unity training trajectory:

\[
\mathcal L_{\mathrm{value}}=(V_\theta(s_t)-z_t)^2
\]

Since the existing wrapper advances a fixed interval after each policy action, the first version can define discounting consistently at that **decision-step level**. The reward coefficients \(\alpha,\lambda\) define the desired behavior; \(\eta_p,\eta_v,\eta_{\mathrm{reg}}\) weight the **training losses**. They are different sets of parameters.

## 9. Implementation sequence

1. **Environment adapter:** Connect to the line-oriented headless protocol; execute and observe actions; preserve the 20-tick wrapper; compute reward components.
2. **MCTS state branching:** Verify deterministic replay; implement a usable branching method with a replaceable interface for snapshot/restore or replay.
3. **Candidate-action generator:** Cover all agreed gameplay categories, respect command semantics, and supply legal candidates to the policy.
4. **Neural network:** Encode the structured state; implement policy and value heads for the variable candidate set.
5. **MCTS planner:** Search Unity-generated futures using network priors and values; select policy actions.
6. **Training loop:** Generate episodes, collect observations/MCTS action distributions/returns, update network parameters, and save checkpoints.
7. **Initial validation and benchmarking:** Confirm the complete observe → generate → search → act → reward → learn loop works; measure computational costs and compare against existing heuristic/simple baselines.
8. **Experimental tuning:** Tune reward coefficients, model/search hyperparameters, and candidate-generation limits; evaluate whether the congestion penalty adds value.

## 10. Evaluation and deferred tuning

Evaluate on **unseen simulated cities/scenarios**, separate from the training and validation data. Track:

- **Completed trips** (primary performance metric, with a consistent simulation horizon).
- **Trip completion rate**.
- **Waiting time**.
- **Infrastructure cost / modifications**.
- **Congestion** (initially an evaluation metric).
- **Planning/training computational cost**, for comparison with heuristic baselines.

Keep the same traffic conditions, simulation horizon, and infrastructure budget when comparing agents, as far as the scenario setup permits. Compare against the **A*-based road-management heuristic** and other simple baselines already discussed.

**Deferred until after the first implementation:** MCTS simulation budget/depth, network size, learning rate and other training hyperparameters, the final \(\alpha,\lambda\) values, any extra reward shaping, congestion-penalty ablations, improvements to the encoder, candidate-generator refinements, and performance optimization.

**First milestone:** a functioning end-to-end AlphaZero-style agent that can observe the Unity city, generate candidate gameplay actions, search hypothetical futures, execute one wrapper action and its 20-tick advancement, receive reward, and update its policy/value network.
