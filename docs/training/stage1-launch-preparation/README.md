# Stage 1 launch preparation — 16 November 2026

No training was authorized or run. This supersedes the earlier status that no
update/launch implementation existed; it does not claim tested learning.

## Implemented

- `hierarchy_batches.py` maps frozen records to manager joint-action and executor
  batches, preserving score-only returns and interruption bootstrap. Partial
  focus cuts cannot be updated; collection continues to a safe boundary subject
  to hard token/time caps. A partial manager selection at operational termination
  uses only its observed primary action, without inventing a secondary action.
- Integration choices: gamma1/lambda1 at both levels (no artificial attenuation
  through paused tokens), explicit equal aggregate role weights with sample-size
  weighting inside each role, and rollout-wide role advantage normalization.
  These are provisional engineering choices, not user review marks or optimality
  claims. Lambda1 increases variance; sparse exploration is still unproven.
- Joint manager entropy uses H(primary)+importance_ratio(primary)*H(secondary|
  sampled primary). This retains the derivative of the primary expectation;
  merely adding sampled conditional entropy would omit it. Frozen behavior
  probabilities/masks/context are stored, and policy versions cannot change
  during an unfinished focus.
- Updater clips the joint manager likelihood ratio once. Gradients accumulate
  over role-balanced minibatches before one shared Adam step per epoch, avoiding
  misleading role weighting from separate adaptive optimizer steps. This is an
  explicit integration variant: four full-rollout optimizer steps, not the old
  flat-policy sixty-four minibatch steps. lr3e-4, clip.2, entropy.01, vf.5,
  norm.5, KL target.02 remain numerical baselines. Epoch-level KL preflight runs
  before any parameter changes. No actual backward/update has been executed.
- `prepare_stage1.py` defaults to dry-run. A deliberate --execute option is the
  only training path and has NOT been invoked. Bounded token/wall budgets, atomic
  trusted-local checkpoints, policy/optimizer/RNG/config identities and progress
  logs are implemented. Checkpoints restart the current episode; simulator state
  is not resumed exactly. Error/partial update states are not saved over the last
  safe checkpoint. No checkpoint or pretrained weights initialize a fresh run.

## Checks actually performed

Forward-only integration with real simulator collection passed at6tokens and
129tokens (128target plus completion of current focus). Both role losses were
finite; parameter fingerprints unchanged and optimizer steps0. A one-token hard
cap interrupted an unfinished focus with no update. Three integration unit tests
passed: both loss paths/known returns, rejection of unfinished focus, temporary
trusted checkpoint roundtrip/config mismatch. Default update-authorization test
passed. Temporary untrained checkpoint files were cleaned. Small statuses/config
are retained here; outputs are diagnostics, not learned results.

No gradient/update, trained-optimizer resume, CUDA integration or Linux-PC timing
has been tested. The first authorized session must be a bounded integration pilot
with finite-gradient/loss/KL/checkpoint/replay inspection, not a long production
run. Full-game tools and automated best-checkpoint/evaluation orchestration remain
outside this initial integration runner; the existing frozen evaluation tool
must be used before claiming curriculum success. Single-worker runner is an
integration baseline, not the fastest3950X/2080Ti configuration.

## Ready-to-run non-training check on Linux after source transfer

```bash
source .venv/bin/activate
bash training/verify_practice.sh
python training/prepare_stage1.py --output output/stage1-preflight-01 \
  --rollout-tokens 128 --minibatch-size 32 --max-tokens 512 --wall-seconds 120
```

Use a new output directory; prior outputs are preserved. The default omits
--execute and performs NO parameter updates. Do not add --execute until the user
authorizes a training session. The implementation is still cloud-local, not
installed on the target PC and not pushed. Do not claim target readiness from
cloud CPU results alone.

Conditional secondary-selection values receive the same realized score-return
target as the primary (no reward/time occurs between selections); per-record
value MSE averages the two present contexts. This trains the conditional critic
needed when a pause interruption ends during manager selection, rather than
bootstrapping an entirely untrained conditional value context. Forward-only
integration checks pass after this addition; actual learning is still untested.
