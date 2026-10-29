# Traffic-light availability comparison

Paste into PowerShell; no training is needed:

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\compare_traffic_lights.py --output output/experiments/lights-test-01
```

This runs 20 games: the same ten seeds5000-5009 with light placement enabled
and disabled, using the frozen overnight validation-best policy. Both conditions
use deterministic play, normal stock and a3600-simulated-second cap. Two evaluation
jobs run concurrently. The protocol records seeds and checkpoint/source hashes
before inference, and tensors are checked unchanged. The disabled policy must
place zero lights. If the output folder exists, choose lights-test-02 instead.

Only light placement actions are masked. Proposed light observations and other
action masks remain identical at a shared state. Later routes, stock, upgrades
and survival can diverge. The agent may still choose light packages when placement
is disabled. This tests light availability for this frozen policy, not an optimized
no-light opponent or isolated physical junction throughput. No debug construction
or stock grants are used. Do not retune/reselect on these test results and call
these seeds fresh again.

At completion, the console prints mean trips with lights ON versus OFF and
better/tied/worse map counts. Full results are saved in
`output/experiments/lights-test-01/comparison.json`. Completed trips is the primary
comparison. Vehicle-waiting averages are descriptive: different survival and load
can confound them. Best replays for each condition are saved alongside the reports.

The full comparison has not been started while preparing this command. A startup
smoke ran only development seed2000 to30 simulated seconds: one trip in each
condition. This is not evidence of light benefit. Three signal integration checks
pass, including normal stock/replay and unchanged observations/non-light masks
when the intervention is applied at a stock-bearing state.
