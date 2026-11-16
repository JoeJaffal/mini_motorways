"""Produce the v1 decision snapshot and concrete seed/config sources. No training."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
original = json.loads((ROOT/'docs/training/decision-tracker-2026-11-16/decisions.json').read_text(encoding='utf-8-sig'))
rows = json.loads(json.dumps(original))
spec = 'docs/training/maskable-ppo-spec-v1-2026-11-16/SPECIFICATION.md'

# ID: selected choice, explanation, rationale, execution work, specification section.
selected = {
'D03':('Fresh policy/value/Adam; no old weights, imitation or statistics','Seed42/43/44 initialize independent random networks and optimizers. Reuse only compatible IPC/build/logging utilities.','Honor user fresh start and prevent inherited training from confounding evidence.','Implement fresh initialization and provenance checks.',1),
'D06':('Freeze938b9f8/f34; isolated Maskable-PPO worktree and Release build','Protocol patch and DLL hashes tracked separately. Do not switch or clean this dirty checkout, merge gameplay or follow moving main.','Source identity makes comparisons reproducible; source/version was inspected.','Prepare isolated workspace, add required adapter-only patches and verify build handshake.',1),
'D13':('Choose center; execute native roundabout placement','Simulator applies its actual footprint, preserved exits, planned activation and stock accounting. Agent chooses additional external links.','Matches accepted TrafficWorld.AddRoundabout, avoids invented automatic road connections.','Implement center mask and source-backed footprint/activation fixtures.',2),
'D14':('Choose motorway endpoints; native create/edit/remove controls','Edit selects existing object by endpoint then new endpoints. Native ramp directions and retirement rules retained.','MotorwayNetwork already supplies this tool; no surface road path generation.','Implement endpoint/object masks and replay tests.',2),
'D15':('Expose connection erase, tile removal and whole-object removal','Road/bridge erasure uses adjacent edge. Tile/circle/motorway removal preserves native side effects and committed-traffic refunds.','Supports fine repairs and full legal delete scope. RemoveRoadConnection exists but adapter/replay dispatch is missing.','Add erase dispatch and replay support without changing game rules.',2),
'D16':('Offer indices0/1; paused explicit choice; no package filtering','All actual offers selectable, including packages with tools outside agent scope. Wait returns early; pending-offer wait is a zero-time no-op.','Use actual UpgradeChoices rather than strategic masks or hidden auto-selection.','Implement offer descriptors and exact package/action masks.',2),
'D19':('Interrupt after4096tokens without positive game-time advance','External truncation, observable counter, no reward penalty/forced wait/legality pruning. Evaluated stall is incomplete and blocks competitive claims.','Bounds a looping policy without changing physical game legality; threshold is engineering, not measured optimal.','Implement counter, live-state bootstrap and explicit stall reporting.',3),
'D20':('Discrete1501 tokens with staged tool/cell/direction operands','Cells0..1499, cancel1500. ROOT0..9 tools; direction0..7; offers0/1. Six observable stages. Each token is a PPO decision.','Supported discrete masked interface avoids endpoint-pair explosion and conditional MultiDiscrete ambiguity.','Implement token schema, prefix validation and cancel behavior.',3),
'D21':('Single direct policy; no explicit goal hierarchy in v1','The policy chooses successive edits from observations. No goal selector, route helper or separate controller.','Minimize additional unvalidated learning mechanisms while retaining model-selected geometry.','Implement one policy and audit forbidden planner/debug access.',3),
'D24':('grid81x30x50, global54, motorway table1500x6','57 static channels,24motion-history channels; exact order and bounded transforms specified. Structured visible fields only.','Represent road direction and pair identities while avoiding hidden schedules and unstable learned scaling. Widths are chosen, not proven best.','Implement schema and visibility/finite/capacity checks.',4),
'D25':('Four distinct-time traffic frames; six observed fields each','Occupancy,mean headings,observed vx/vy,stationary fraction. History validity/ages supplied; paused edits do not create new motion frames.','Recent visible displacement distinguishes queues from flow without leaking internal routes or waits.','Implement timestamped tracking, missing frames and sampling checks.',4),
'D27':('Raw score_after minus score_before on each token','No shaping/penalty/bonus/reward normalization; episode sum reconciles exactly to score change.','Direct realization of the user score-only objective.','Implement telescoping check and terminal/cap handling.',5),
'D28':('gamma1.0; GAE lambda.95; correct terminal/truncation bootstrap','Finite3600s task horizon; zero-time selections do not discount trips. GAE still approximates credit. External interruptions bootstrap live value.','Align undiscounted score with pause semantics; acknowledge higher variance and unproven sparse-reward learning.','Verify bootstrap paths and log credit/value diagnostics.',5),
'D29':('Train4cities; hold out London; fixed disjoint seed sets','Train128seeds/city10000..10127,validation16/city20000..20015,test50/city30000..30049. London40000..40049. Learners42/43/44.','Implements user split; London offers stringent rail-city transfer. Seed lists chosen without outcome selection.','Use archived split_manifest.json; never train or tune on London outcomes.',7),
'D30':('No curriculum; balanced cities and shuffled128seed cycles','Round-robin cities across episodes, seeded shuffle per city; full native starts, no favorable state resets or100-game seed blocks.','Avoid simultaneously introducing curriculum and preserve variety in a clear first baseline.','Record/reset sampler state and learner RNG.',7),
'D31':('20paired first-attempt human/agent games; same pause/tool/horizon rules','Five final seeds per training city; one3600s game per party/seed. Record prior exposure and perception/reaction differences.','Compare directly with user under matched simulator conditions; missing human scores are execution work.','Collect human scores after development freeze; no request needed tonight.',8),
'D32':('Per-city distributions, completion rates, baselines and uncertainty','Compare untrained,uniform-legal-token and wait/first-offer diagnostics; deterministic primary, sampled validation secondary. No planner baseline.','Separate robust policy behavior from lucky highlights and expose stalls/errors.','Implement fixed cohorts, metrics and10000resample intervals.',8),
'D33':('Evaluate each16384tokens; select by complete64game validation cohort','Periodic8games; incumbent/final comparison64each. Rank equal-weight city mean, then lower spread, then earlier timestep. Incomplete cohort cannot promote.','Fix selection before outcomes and prevent lucky/per-map checkpoint cherry-picking.','Implement mask-aware evaluation inside overall wall caps.',8),
'D35':('Frozen64game cohort; best/worst/nearest arithmetic mean','Tie by city order then seed. Preserve all validation logs,three selected replays and additional stalled/error games. Provisional label if incomplete.','User can review actual comparable episodes from the same policy; no synthetic average game.','Implement replay selection and score/time reproducibility.',8),
'D36':('Small CNN plus global/pair encoders; separate actor/critic','CNN81->32->64->64,pool4x7->256;global54->64;paired motorway MLP6->32->32 mean/max64;concat384->256;actor/critic128hidden.','Spatial geometry plus exact motorway pairs with limited components; no unsupported recurrent MaskablePPO. Sizes are baseline choices.','Verify shape/count from checker, then implement feature extractor.',5),
'D37':('2env x1024steps,batch128,4epochs,lr.0003,clip.2,entropy.01','gamma1,lambda.95,targetKL.02,valuecoef.5,gradientclip.5,normalized advantages,no value/reward clipping or reward normalization.','Conservative reference-scale baseline; fewer reuse epochs and KL stop limit update exposure. No optimality claim.','Implement exact config and record updates/memory/KL/entropy.',6),
'D38':('Pinned verified CPU stack; .NET SDK8.0.427 Release','Python3.12.14,torch2.14.1+cpu,gymnasium1.4.0,SB3/contrib2.9.2,numpy2.5.4. Recreate isolated environment;seed/determinism provenance.','Existing local versions were inspected; avoid unverified GPU changes and record cross-machine reproducibility limits.','Create clean lock/import/pip check and handshake, not assume installed stack is run-ready.',6),
'D40':('CPU on both initially;2hosts,torch2 intraop/1interop;independent runs','Laptop development/pilot,verified desktop longer runs. No distributed learner,weight averaging or mixed-version rollout. GPU variant is outside v1.','Conservative known hardware/software baseline; reported GPU strength is not measured task speedup.','Verify desktop and record component timings before changing device configuration.',6),
'D41':('3600sim-second finite benchmark or game-over; external limits truncate','Remaining horizon visible; task horizon terminated,not loss. Operational pause/wall truncations bootstrap and are reported incomplete.','Bounded comparable score objective with correct Gymnasium horizon semantics.','Implement end-reason and bootstrap tests for all boundaries.',7),
'D42':('Planned pilot32768tokens/15learner minutes;30minutes overall','No launch tonight. Need8full updates,finite diagnostics,all integration checks and verified save/reload/replay. Follow-on3seeds x1048576tokens/4learner hours,5h overall per seed only if authorized.','Finite integration budget; no automatic escalation or claims a short pilot should reach human play.','Implement and pass preflight, present runnable command before any authorized launch.',9),
}
for r in rows:
    if r['id'] not in selected:
        continue
    choice,explanation,reason,nxt,section=selected[r['id']]
    r.update(choice=choice,explanation=explanation,reason=reason,next=nxt,
             decision='Done',review='Not reviewed',work='Not started',
             basis='Agent-selected; not user-reviewed',date='2026-11-16',source=f'{spec} (section {section})')

# Preserve the reviewed choice/reason, while making its execution follow-up current.
followup={
 'D01':'Collect human scores and apply the selected paired benchmark in D31/D45.',
 'D02':'D44 delegates overnight selections; new decisions still await user review.',
 'D04':'Implement the selected architecture/configuration in D36-D38.',
 'D05':'Build pinned f34 and verify source/protocol handshake according to D06.',
 'D07':'Implement native controls selected in D13-D16 within the approved tool scope.',
 'D10':'Implement staged neighboring connection encoding from D20.',
 'D12':'Implement incremental water masks and native span accounting using D20 encoding.',
 'D22':'Implement exact input schema from D24-D25 and audit field visibility.',
 'D26':'Implement D27 raw-score reward and D28 credit settings; these details await user review.',
 'D34':'Implement frozen-cohort replay selection from D35.'}
for r in rows:
    if r['id'] in followup:r['next']=followup[r['id']]

extra=[
('Delegated decisions','Agent completes remaining design; do not mark user-reviewed','User explicitly delegates all remaining decisions while sleeping. Prior approvals remain historical; new selections are marked Not reviewed.','This instruction permits concrete engineering choices without repeated questions. It does not authorize training.','Document new selections separately from user approvals.',1),
('Competitive milestone','Median paired score ratio >=1; >=10wins/20; all games complete','Ratios use max(human score,1); report zero scores,paired95% bootstrap CI. Lower endpoint>1 needed for a superiority claim.','A predefined operational target makes compete with me assessable; threshold is engineering, not a claimed result.','Implement paired report after human scores exist.',1),
('Integration protocol','maskable-direct-v1 with erase and exact-mask/wait/replay support','Freeze f34 physics; record protocol patch and binary hashes. Ordinary host/replay lacks connection erase; require dispatch rather than substituting coarse removal.','Source inspection identifies concrete missing integration, not a simulator defect or permission to change rules.','Build adapter,validators and replay handling in isolated experiment workspace.',2),
('Final-test discipline','Freeze development before testing4cities and London','50testseeds/city; three preselected learner checkpoints. Final outcomes cannot choose mode/config/checkpoint; retuning requires new final evidence.','Protect unseen-city and within-city evidence from validation leakage.','Execute once after development freezes; retain test provenance.',8),
('Save and resume','Safe checkpoint each2048tokens; retain16384periodic/best/final','Atomic writes and local-only model files. Hash checkpoints/config/build. Resume weights/optimizer/sampler RNG but reset simulator episodes and discard partial rollouts; label fresh-episode continuation.','Make interruptions recoverable without fabricating exact continuation or losing evidence.','Implement checkpoint and replay/source/config manifests.',9),
('Preflight and stop gates','Zero integration defects; stop on nonfinite/schema/mask/replay errors','1000legal-prefix fixture checks;source/score/clock/reward/bootstrap/stall and save/reload tests. At least8finite updates for pilot integration pass; no score-improvement gate.','A broken interface must not be interpreted as poor learning. Sparse reward is a learning question, not grounds for hidden assistance.','Execute gates after implementation; current checks are specification-only.',9),
('Hardware measurement','Five1000-token frozen-observation batches; no learning','Separate simulator/encoding/mask/inference/optimizer/log costs. Optimizer timing,if run,clearly labeled bounded learner work. No measured throughput yet.','Avoid estimating useful-play time from raw CPU/GPU specifications. Numeric protocol is a chosen diagnostic budget.','Profile the implemented workload and verify desktop before allocating longer runs.',6),
('Initial scope boundary','No curriculum,GPU experiment,goal hierarchy or auto-tuning in v1','Low scores trigger documented diagnosis and a new configuration revision,not automatic reward shaping or generated routes.','Keep initial evidence interpretable and honor user strict constraints.','Review measured failures before authorizing changed experiment scope.',9),
]
for topic,choice,explanation,reason,nxt,section in extra:
    rows.append(dict(id=f'D{len(rows)+1:02}',topic=topic,choice=choice,decision='Done',review='Not reviewed',work='Not started',explanation=explanation,reason=reason,basis='Agent-selected; not user-reviewed',next=nxt,date='2026-11-16',source=f'{spec} (section {section})'))

assert len(rows)==51 and all(r['decision']=='Done' for r in rows)
assert sum(r['review']=='Reviewed' for r in rows)==18
assert sum(r['review']=='Not reviewed' for r in rows)==33
for old,new in zip(original,rows):
    if old['id'] not in selected:
        assert {k:v for k,v in new.items() if k!='next'}=={k:v for k,v in old.items() if k!='next'},'Earlier approved choice/reason/review was changed'
    else:
        assert new['review']=='Not reviewed'
(DEST/'decisions.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')

cities=['LosAngeles','Beijing','Tokyo','DarEsSalaam']
manifest={'training':{c:list(range(10000,10128)) for c in cities},'validation':{c:list(range(20000,20016)) for c in cities},'within_city_test':{c:list(range(30000,30050)) for c in cities},'transfer_test':{'London':list(range(40000,40050))},'human_paired':{c:list(range(30000,30005)) for c in cities},'learner_seeds':[42,43,44],'note':'human_paired is an intentional subset of within_city_test; other splits are disjoint by city,seed'}
sets={k:{(c,s) for c,seeds in manifest[k].items() for s in seeds} for k in ['training','validation','within_city_test','transfer_test']}
for i,a in enumerate(sets):
    for b in list(sets)[i+1:]:assert not sets[a]&sets[b]
(DEST/'split_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
config={'protocol':'maskable-direct-v1','source':'938b9f80e67ca5341920a10e9e671164a474fc38','simulator':'2026-11-10.f34','rules':'OriginalReference','variation':'SameMap','review':'NOT USER-REVIEWED: engineering-selected','training_authorized':False,'action_tokens':1501,'root_actions':['wait','road_or_bridge','roundabout','new_motorway','edit_motorway','erase_connection','remove_tile','remove_roundabout','remove_motorway','weekly_choice'],'stages':['ROOT','CELL_FIRST','DIRECTION','OBJECT_CELL','CELL_SECOND','OFFER'],'grid':[81,30,50],'global_features':54,'motorway_table':[1500,6],'history_frames':4,'wait_ticks':20,'tick_seconds':0.05,'horizon_seconds':3600,'stall_tokens':4096,'device':'cpu','workers':2,'torch_threads':2,'torch_interop_threads':1,'ppo':{'n_steps':1024,'batch_size':128,'n_epochs':4,'learning_rate':0.0003,'gamma':1.0,'gae_lambda':0.95,'clip_range':0.2,'target_kl':0.02,'ent_coef':0.01,'vf_coef':0.5,'max_grad_norm':0.5,'normalize_advantage':True,'clip_range_vf':None},'pilot':{'tokens':32768,'learner_wall_minutes':15,'overall_wall_minutes':30},'follow_on_if_authorized':{'tokens_per_seed':1048576,'learner_wall_hours_per_seed':4,'overall_wall_hours_per_seed':5,'learner_seeds':[42,43,44]},'checkpoint_tokens':2048,'evaluation_tokens':16384,'dependency_pins':{'python':'3.12.14','torch':'2.14.1+cpu','gymnasium':'1.4.0','stable-baselines3':'2.9.2','sb3-contrib':'2.9.2','numpy':'2.5.4','dotnet_sdk':'8.0.427'}}
(DEST/'CONFIG.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'records':len(rows),'new_unreviewed':33,'prior_reviewed_preserved':18,'unresolved_design_rows':0,'train_pairs':len(sets['training']),'validation_pairs':len(sets['validation']),'final_pairs':len(sets['within_city_test'])+len(sets['transfer_test'])}))
