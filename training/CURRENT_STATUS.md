# Simulator repairs after resume — 8 November 2026

[Report](../docs/training/simulator-repairs-2026-11-08/README.md), [re-evaluation handoff](../simulation/Docs/HANDOFF-2026-11-sim-fix.md). Reward-v4 drift isolated to the intended rule-77 native join (new fixture v5); stale `Waiting` on arrival fixed; additive `simulatorVersion` (`2026-11-08.2`); permanent roundabout/junction yield-cycle deadlock proven and fixed; v21 regenerated from the builder with the seven handoff corrections (topology check passes 400/400). 79 core/7 environment/6 reward-v5/10 map PASS. A physical adjacent-junction gridlock ends v21 and awaits a user rule decision; Unity player not rebuilt; no training or push. Earlier PPO/Evolved Rules results are valid only for their simulator version.

# Missing-file handoff ready locally — 8 November 2026

[Transfer bundle and review response](../docs/training/full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). Verified2368payloads,924MiBlocalZIP; no external upload. Simulator work remains stopped in this handoff iteration. Source77checks from Aya are recorded; reward-v4drift remains unexplained. No engine/fixture/training change.

# Resume check: reward-v4 regression found — 8 November 2026

[Resume review for approval](../docs/training/full-replay-review-2026-11-08/RESUME_REVIEW_FOR_APPROVAL.md). Committed 77-suite source (`f7ce005`, including the dedup edit) re-checked on another machine: 77 core PASS, 10 map PASS; environment 6/7 (missing local `tmp/` only); **reward v4 FAILS: ordinary LA fixture now 23 trips/no game-over vs 13/game-over**, so the 75–77 changes alter ordinary play (cause not yet isolated). No engine, fixture or test changes. Awaiting Mohammad's approval and local files; no training.

# EMERGENCY STOP — 8 November 2026

User requested stop/save. [Saved state and exact continuation plan](../docs/training/full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md). Installed74-suite player; source77candidate ahead, final small dedup edit not retested. No active matching diagnostics found. Full replay/parity unvalidated; do not resume automatically. No training.

# Shared-carpark replay repair under verification — 8 November 2026

[Full review](../docs/training/full-replay-review-2026-11-08/README.md): shared-lot through-routing independently implemented; initial71core/7environment/6reward/10mapPASS. Erased old motorway endpoint cleanup72PASS. v15reaches371/game-over957.05s with shared outside-turn deadlock; approach-boundary correction and bent mixed-flow regression pending. Strict input reconstruction435events still incomplete; partial scores are not a valid835comparison. Installed69-rule player unchanged. No learning, grants or score fitting.

# Full replay input review in progress — 8 November 2026

[Current work](../docs/training/full-replay-review-2026-11-08/README.md): user accepts opening and authorizes independent continuation.55observed houses; navy top/latergreen left entrances corrected; per-second registration and manual road screening. v13candidate stops at832.95s/286trips on rejected material after195/443events, NOT a valid original835comparison. Continue input/stock validation;69-rule engine unchanged, no learning or grants.

# Replay inputs under review; opening checkpoint layouts verified — 8 November 2026

[First60video seconds reviewed](../docs/training/replay-input-validation-2026-11-08/README.md): native-stub false road draws/orphan cells removed, red west→north driveway corrected.16events,7manual topology/direction/stock checkpoints PASS (old2/7); existing player loads6/90/16 and reviewed clip opened paused. No simulator tuning this iteration. Full input/timing/video-speed synchronization and original performance parity remain unvalidated/NOT_MATCHED; no learning.

# Identical performance required; event parity NOT matched — 8 November 2026

[Current audit](../docs/training/event-parity-2026-11-08/README.md): missing movement factor3 and ordinary weighted/motorway minimum lookahead corrected,69 core checksPASS. First delivery17.45vs original estimated17.418, but2late~2.2s and3early~6.3s.330s50trips/no failure is improvement, not parity. Unknown original hidden state and invalid later trace remain. 69core/7environment/6reward-v4/10map-version PASS; Unity prefix50/330/99 and normal startup verified, corrected player installed/backed up and prefix reopened paused. Original observed-event gate NOT_MATCHED (exit1). No learning or score-fitting.

# Early carpark performance repair installed — 8 November 2026

[Repair record](../docs/training/video-performance-repair-2026-11-08/README.md): identical297.45s input24/failure→30/no failure; red deliveries2→9. At330s37trips/no failure/no>20s waits.67 core/7 environment/6 reward/10 map-version PASS. Boundary entrance reservations and bay merge clearance fixed without demand/stock/seed tuning. Corrected player installed/backed up; Unity prefix37/330/99 and normal city smoke PASS. Reopened prefix330 paused for watching. Full trace still invalid later; no exact835 comparison. No learning.

# Custom seeding installed; video comparison preliminary — 8 November 2026

[Feature/result record](../docs/training/custom-video-scenario-2026-11-08/README.md):58 core suites, Unity example4/80s/5events, recorded draft24/297.45s/84events and ordinary seed12345 smoke PASS; corrected player installed with backup. [Usage](../simulation/Scenarios/README.md). Original final835 vs reconstructed24 (-811) is PRELIMINARY, not validated same-seed parity:1s samples, unknown original hidden state, future696/780 events unapplied after early game-over. Red carpark clearance/merge waits>139s reproduce; static same-network control clears22trips/400s, so queue-sequence mechanism remains open. No traffic-rule tuning to835 or learning. User's custom-seeding request supersedes freeze below only for this feature/reconstruction.

# Gameplay changes frozen for uploaded-game comparison — 8 November 2026



[Recorded-game evidence](../docs/training/recorded-game-comparison-2026-11-08/README.md): original final visible HUD **835** (826 was paused). Exact seed/event replay unavailable; matched simulator score/delta not measured. User says no further changes; gameplay/build/settings frozen, reconstruction clarification pending. [Prior repairs/deployment](../docs/training/gameplay-fidelity-repairs-2026-11-08/README.md):54 core/7 environment/6 reward/10 map checks and5 installed Original city smoke passes. Exact parity still unvalidated. No learning/promotion; earlier training results remain historical.



# Relative-input test complete: no measured improvement — 8 November 2026



[T107verifiedreview](../docs/training/relative-branch-review-2026-11-08/README.md). USER2×1000updates/~5m56complete, no newlearning. Actualnew+576columns learned, differentlosses/probabilities; all1624caseoutcome/costrecords matchT103baseline. FINALFIT119/120of124,layout34/31of44; BESTlayout30/32of44, all<80%. Prior144FIT/48layout/32linesretained.87/88FINALdevelopmentactionsequences unchanged, alteredcaseoutcomesame; traininggreedychoices0/1296and1/1311differ.1624exactreproductions/2000batchhashes/teacher/Adam/counters/source/control/protected4/nativepairs verified. No measuredbenefit, don'tpromoteorextendthisvariantwithoutnewevidence; simplerbranchreferencekept, notproduction. Nextproposeddistinctspatialreasoning/learninghypothesisreview beforeanotherchange; no nextcommand/run. Userlauncheslearning, binarieslocalonly/no sourcepush/finalmaps.



# Controlled goal-relative feature test ready for USER launch — 8 November 2026



[T106command/checks/budget](../docs/training/relative-branch-preparation-2026-11-07/README.md), nolearning. T105352freecaseaudit: wrong-next-goal-after-usable-road category8→1; paired6oldcasesrescued,2stillfailwithdifferentfirstroads. Anycomponentone-strokefinishverified1/23remainingbranchfailures; normal2extrastrokerepair23/23feasible, oracleonly. Serializationbugv1fixedbool/v2preserved, no modelchange.



Reuseexisting+576goal-relativecandidate onEXACTT103data/objective/samplers/source750; oldnegativeextensionresult acknowledged. All2607initialactor/valueoutputs EXACTmatchhistoricalbranchbaseline, all2000batchhashesmatch,3checks/preflightPASS. TwoUSERrelative-onlyruns1000updates/180s each/900soverall; sameBESTFINALbothseedphysical/retentiongates. No newmodeloutcome/sourcepush/promotion/finalmaps; weights/datahostlocalonly. Userlaunchesalllearning; currentgatefailed.



# Branch teaching completed: training improves; development gate FAILS — 7 November 2026



[T104verifiedreview](../docs/training/branch-teaching-review-2026-11-07/README.md). USER2×1000updates/~5m20complete, no newlearning. FINALfullFIT119/124,120/124 vscontrol109/114; layout34/44,31/44 vscontrol31/31, mixedtransfer. BEST250/750layout30/44,32/44. All4snapshotsbelow80%(need36/44); no promotion. Prior144FIT/48layout/32linesperfect, old48FIT46/47FINALand48/48BESTpasses.1624exactepisodereproductions/2000batchhashes/teacher/Adam/counters/source/control/protected4hashes/bothnativepairs verified. Historicalcontrolsnotrerun. Nextproposedremainingfailure/gained-lostcaseauditwithvalidroad/nextgoalchecks; no newtrainingcommand. Userlauncheslearning; binarieslocalonly/no sourcepush/finalmaps.



# Branch-consistent teaching ready for USER launch — 7 November 2026



[T103checkedcommand/budgets](../docs/training/branch-teaching-preparation-2026-11-07/README.md). T102correctsdiagnosis: manycanonicalmismatchesvalid,12currentFITand12earlierdevelopmentfailures haveusefulfirstroads thenrestartconnectedgoal. NewFITacceptedsets+matchingcontinuations prepared:40/45verifiedalternatives,120/135suffixstates,5checks/versionguard/preflightPASS. No learning. ReusecompletedT100cleancontrols withmatchedstarts/2000batchhashes/packageversions; only2newbranchruns1000updates/180seach/900srunloop, noextensions. SameBEST/FINALbothseedphysical/retentiongates. Runtimefullylearned/no maskorNNchange. OldT101gatefailed/no promotion/sourcepush/finalmaps; binarieslocalonly. Userlaunchesalltraining.



# Comparison completed; guard protected results; both arms FAIL — 7 November 2026



[T101 verified review/guard explanation](../docs/training/recovery-comparison-review-2026-11-07/README.md). ExistingpathscontainCOMPLETED4USERruns,1000updateseach,11m53. Fresh-outputerrorblockedadditional launch; no rerun/deletionneeded. No newlearning.3248exactepisodereproductions,4000batchhashes/counters/Adam/teacher/pairedstarts/native4pairs/protected4hashes verified. FINALcleanlayout31/44both (70.45%), recovery32/44,33/44(72.73/75%), allbelow80%. Recoverytradesmorecleanrouteforgetting forsmalllayoutgain: cleanFIT109/124,114/124 vsrecovery106/124,108/124;old48FIT44/46vs42/41. BothBEST/FINALbothseedgatesFAIL. Prior144FIT/linesretained, priorlayoutclean48/48both vsrecovery44/48,47/48. No winner/promotion. NextPROPOSED first-bendauditwithvalidalternatives beforeanotherchange; no newcommand. Userlauncheslearning; sources/weightslocal/uncommitted, no finalmaps.



# Matched clean/recovery study ready for USER execution — 7 November 2026



[T100 command/limits/checks](../docs/training/recovery-comparison-preparation-2026-11-07/README.md). No learningstarted. Within#8/#12/#15, decision057.124cleanFITcases/744states+432prior and78/48source-specificverifiedrecoverystates; no developmentteaching. Fourruns clean/recovery×101/202, matched96batch andbest750actors,1000updates/180s each/720summed/1800runloop,noextensions/earlyfitstop. Fivechecks/preflight andbothseedstartmatchingPASS. BothBEST/FINAL/bothseedsrequire full90/80+old48FIT90+prior90/80+line90/0rejects. Best/native replay/hash/step+final/error planned. Models/outputs unchanged, userlaunchesalllearning. No winner/resultyet, T98transfergatefailed, oldskillspreserved. No sourcepush/promotion/finalmaps; binarieslocalonly.



# Complete technical audit delivered — 7 November 2026



[Professional 30-page PDF](../docs/training/complete-technical-audit-2026-11-07/mini_motorways_complete_technical_audit_2026-11-07.pdf), T100; presentation conversion only, no new findings or learning.



[Independent audit and proposed roadmap](../docs/training/complete-technical-audit-2026-11-07/REPORT.md), T99. Latest checkpoints are supervised goal-conditioned construction policies, not latest PPO training; earlier PPO/hybrid infrastructure exists separately. Fresh frozen development25/44 and30/44, zero rejects, gate still failed; no full-game/Steam/SUMO learning claim. Documentation only, no learning/source change. Await researcher approval before implementation. Earlier status below stays historical.



# Full-route diagnosis: first-leg selection and recovery — 7 November 2026



[T99 frozen evidence/proposal](../docs/training/full-route-diagnosis-2026-11-07/README.md). NO LEARNING/weightchange.368freeepisodes reproduceoutcomes; all33FINALdevelopmentfailurepairs startoutsideaxis-templatelegs thenrepeat no-progressroads. Offlineone-endpointinterventionrescues31/33, later-noopcorrection21/33; assistedresults NOT modelperformance.31/33failures alreadyhaveseenFITgoaloffset, so missingdistancealoneunsupported. Unused76FITworldcases:62/76,68/76; all22failures(15distinctlayouts) samebehavior, physicallyqualified. 6native replaysPASS, fourcurrentactorhashes matchT98/unchanged.



NextPROPOSED matched-budget broadercleanFIT vsbroaderclean+verifiedrecovery, priorrehearsal, source-specificFITonly rollouts; draftnotexecutable/norun. Full-routegate remainsFAILED, prior skillspreserved. No newtrainingcommand, sourcepush, modelpromotion/finalmaps. Userlaunchesalltraining. Mechanism/benefitofproposeddatachangeunproven.



# Full-route training completed: transfer gate FAILED — 7 November 2026



[T98 verified results/limits](../docs/training/full-route-review-v2-2026-11-07/README.md). USER2×1000supervisedupdates,5m12complete; no newlearning. FINALfullFIT47/48,48/48; layout25/44,30/44 vsINITIAL25/44,32/44: transferunchanged/regressed. Best750FIT-onlyselected,layout25/44,26/44; bothsnapshots/seedsfail80%full-layoutgate. PriorFIT144/144both/layout48/48,47/48/line32/32 retained. All1320episoderecords exactlyreproduced, teacher/counters/Adam/source/data/build/protected4hashes/nativepairs verified. Reviewtuple/listbugfixedwithnormalizedcomparison, failedattemptpreserved. Canonicalteacher717/720isnotgeneralization. NextPROPOSED failuretrace/actualgeometryaudit before broaderFITorrepresentationchange; no nexttrainingcommand. Userlaunchesalllearning. No sourcepush/promotion/finalmaps; binarieslocalonly.



# Empty-start full-route lesson ready for USER launch — 7 November 2026



[T97 plan, checks and exact command](../docs/training/full-route-preparation-2026-11-07/README.md). User launches training again, ending overnight exception (decision056/AGENTS). NO LEARNING STARTED.720FITstates:288new+432prior;48new and58developmentphysicalqualifications,0setup/rejects; developmentteacherstates0. Fourtests/preflightPASS. Bothcontinuedbest250sources,1000updates/180sperseed/360summed/900runloop; batch96, noextensions. BOTHbest/FINALandbothseedsmustpassfullroute90/80,prior90/80,line90,0rejects. Best/replay/update/hash+final/error planned, FIT-onlyselection. Existingextensionpassretained, full-routegateawaited. No PPO/productionpromotion/finalmaps/sourcepush; binarieslocalonly.



# Scaffolded extension PASSES; empty-start route next — 7 November 2026



[Verified autonomous block](../docs/training/overnight-progress-2026-11-07/README.md), T92–T96. User authorizes assistant-run bounded work until further notice (decision054), superseding manual-only rule. Four studies complete, no learning left running. Expanded FINALboth144/144FIT,47/48layout,16/16longer,32/32line; FIT-selectedBEST250both144/144FIT,layout46/48,47/48,16/16longer,32/32line. Paired90/80/90scaffolded subgatePASS; not fullissue8/fullgame. No PPO learning/inferenceplanner; same architecture/legal rules. Best/native/hash/Adam/teacher/reload checks and protected4hashes pass. Sources/weights local/uncommitted, no promotion/finalmaps.



Empty-start full-route frozenFIT34/48,35/48,0setup;48normalwitnesses verified/deduplicated. [Next audit/demos/non-executable draft](../docs/training/full-route-readiness-2026-11-07/README.md). No full-route learning launched. Next corpus/duplicate/observability/retention checks then bounded paired training; do not skip to fullgames. GitHub1/8/9/12/15updated/allOPEN. Critical self-review required.



# Tiny first-click diagnostic ready for USER execution — 7 November 2026



[T91 preparation, limits and exact command](../docs/training/first-click-overfit-preparation-2026-11-07/README.md). No learning started. Four no-learning checks and pinned/fresh preflight pass. Warm/scratch, one then gated four known FIT mistakes; maximum500 updates/45s per stage,180s summed stages/300s cooperative run-loop budget. Conditional memorization only, not full-game evidence. Initial/final/error and best matching replay/hash planned. Existing physical gates FAILED; #8/#9/#12/#15 stay OPEN. User launches all learning. Decision053 requires critical review and evidence/hypothesis separation throughout this chat.



# Objective assessment recorded; capability gate still failed — 7 November 2026



[Assessment and proposed go/no-go diagnostic](../docs/training/project-assessment-2026-11-07/README.md), T90. Currentmodel not validatedforfullgames; pipelineprogress ≠ skillprogress. Tinyfirst-click overfit/correctness audit recommended before more broadpilots; no numericalsuccessodds/timeline or newmodel/learningbudget decided. CurrentT89failure remains, #8/#9/#12/#15OPEN. No code/model/training/sourcepush/promotion change.



# Consistent-order teaching completed: first-click gate still FAILED — 7 November 2026



[Verified canonical results/audits](../docs/training/canonical-imitation-review-2026-11-07/README.md), T89. Four300-update/batch24runs complete50.72slearning/174.32sinclusive(2m54),7200examples each. Allfitdet5/48/layout7/48,line32/32;sampledfit48/48,layout36/48 or39/48;longerdet0/16,full-detour0/16. No arm passes. All896finalrecords exactlyreproduced, source/data/host/counters/Adam/reload/protectedhashes and4nativebestreplays verified.



Teacherphase tool48/48,first5/48,end48/48 inallmodels; all43firsterrors selectgoalalreadyonprefix.144uniqueinputs/no contradictoryduplicates. Aggregate first/end cellheadgradient cosines+.606–.774: opposing-gradient hypothesis NOTsupported atfinalweights; causeunresolved. Bestupdate0all (priortrainededgeactors), notnewlessonimprovements. NextPROPOSED focusedfirst-clicklearnabilitydiagnostic, notimplemented/trainingauthorized. #8/#9/#12/#15OPEN,no promotion/sourcepush/newfinalmaps. No newtrainingcommand or modelchange.



# Consistent-direction teaching ready for USER execution — 7 November 2026



[Canonical data, checks and command](../docs/training/canonical-imitation-preparation-2026-11-07/README.md), T88/decision052.144FITstates from48existingfixtures:Draw→unconnectedgoal→roadend.48fullsequences/96normalcommands verified; all observations/masks identical to source, no newruntime teacher/strategicmask. Newdata narrows validteachingorder, does not declare oldlabels incorrect.



Samebaseline/relation×101/202;300updates,batch24,50passes/7200examples each;120s/run/480stotal/900sinclusive. Best/replay/BCcounter semantics and full90/80/90physicalgates retained. Data coverage/phaseweighting/batch differ from oldprobe; no pureloss-only/equalexamplebudget claim. Directionunit+realgradient/save/replay+guard/preflight checks pass, NO TRAINING STARTED/output/resultsabsent. #8/#9/#12/#15OPEN, no sourcepush/promotion/finalmaps. User launchesalllearning.



# Correct-example teaching completed: physical gates FAILED — 7 November 2026



[Verified results and specific error](../docs/training/construction-imitation-review-2026-11-07/README.md), T87. Four models complete300supervisedupdates/9600examples each,57.32sinsidelearning/176.03sinclusive(2m56). Botharchitecturesfit10/48,12/48; layout6/48all; sampled47/48fit and35/48,39/48layout; line32/32all, unscaffoldeddetour0/16all. Teacherloss~.282, greedylabelaccuracy60–63%; physicalgatesunchanged/failed.



ALL896finalfixture records exactly reproduced, counters/Adam300/unchangedvaluehead/source-data-host hashes/reloads and4nativebestreplays verified; no reviewoptimizersteps. Teacherstate errors ALLselect thegoal already onprefix: firstclick10/48,12/48correct; roadend→goal9/48,13/48 vs reverse48/48both.192uniqueinputs/no contradictoryduplicates. NextPROPOSED consistentdirection demonstrations, notimplemented or provenfix; no inferenceplanner/strategicmask. #8/#15/#9/#12OPEN, no promotion/nexttraining/sourcepush/finalmaps. Currentweights BC-tagged/PPO-readyFalse.



# Video teaching references catalogued; imitation pilot unchanged — 7 November 2026



[Publicvideo research and limitations](../docs/training/video-teaching-research-2026-11-07/README.md), T86/decision051.5video/2officialtextreferences, metadata/descriptions only, no frames/transcripts/actions verified and no currentworldrecordcertified.0video labels added. Futuretimecodedreconstruction/replay/teacherquality procedure proposed; no deployedplanner.



[Current192FIT-state teachingpilot](../docs/training/construction-imitation-preparation-2026-11-06/README.md) remainsready with unchangedsource/data/plan,15minUSERcap,bestmodel/replays. No trainingstarted/output/resultsabsent. #8/#15/#9/#12OPEN; researchdoesnotblockcurrentpilot. No sourcepush/modelupdate/promotion/finalmaps.



# Correct-example teaching pilot ready for USER execution — 6 November 2026



[Plan/data/contracts/checks](../docs/training/construction-imitation-preparation-2026-11-06/README.md), T85/decision050. Fit-only192states from48fixtures,96physicaltwo-direction completions/192normalcommands,2.58sgeneration. Set-valuedmaskedactorloss accepts bothcorrect firstcells; no teacher atplay/heldlabels/PPOlearning. Existingbaseline/relation×101/202 matchedprioractors;300Adamupdates×32examples each,120s/run/480stotal/900sinclusive max.5focused/regression tests+real gradients/unchangedparams+save/reload/native replay+preflight pass; NO TRAINING STARTED.



Supervisedupdate/examplecounts separate fromzero RL/PPOcounters; valuehead nottrained/sharedencoderchanges, PPO-readyFalse. Bestmodel/replay at0/100/200/300supervisedupdates; originalphysicalfinalgates unchanged, teacheraccuracydiagnosticonly. #8/#15/#9/#12OPEN; optionaloffline-teaching diagnostic, not newtournament/PPOcomparison/fullgameproof. DatasetNPZ ignoredlocal-only, manifest/sourcearchived; output/resultsabsent. Userlaunchesalltraining, source/docslocal/no push/promotion/finalmaps.



# Completed runtime comparison: both learner gates FAILED — 6 November 2026



[Verified fullresult](../docs/training/runtime-comparison-review-2026-11-06/README.md), T84. Userrun4×4096steps completes202.17sinsidelearncalls/386.18sinclusive (6m26),0errors/caps/rejections. Runtime/recording nowwork. Baseline finalfit10/48,5/48;layout10/48,3/48; relationfit13/48,7/48;layout7/48,9/48. Sampledlayoutbaseline42/48,41/48vsrelation38/48,39/48; lines32/32all,full-detour0/16all. Neitherpasses unchangedgates/no consistentcandidateadvantage.



ALL896finalfixture records reproducedexactly withoutlearning; source/plan/host/fixture/source/protectedhashes,updates/reloads/finiteweights and4nativebestreplaysverified. Relationbeststep0both (pretrainingforthislesson), baselinebest2048both;12caseFITscreens notgate. No model/lesson/algorithmchange or promotion. #8/#15OPEN. NextPROPOSED optionalfit-only teaching/representability-vscredit probe, notimplemented/authorizedlearning; explainbeforecode, userlaunchesalltraining. No nexttrainingcommand/job. Source/docslocalmohammad,no push.



# Awaiting fresh v2 terminal evidence — 6 November 2026



Userthinksdone, but v2output/resultsabsent and noPythonprocess. Latestlocalrun isfailedv1; exactv2no-learningpreflightPASS. [Returncheck](../docs/training/runtime-v2-return-check-2026-11-06/README.md), T83. Needterminaloutput/actualcommand/machine; no newoutcome or failure inferred, no assistanttraining/codechanges. Previousreadyplan remainsavailable.



# Permission-writer repair ready for fresh USER retry — 6 November 2026



[Failed v1 evidence/fix/new command](../docs/training/runtime-permission-repair-2026-11-06/README.md), T82. UserprovidedPermissionError; artifactsnowexist (supersedesT81missingevidence). Initial48caseassessment completes14successes, then summaryfinalization deniesaccess;0learningsteps/updates, initial/errorweightsidentical. Exactlockholder unproven. Uniqueclosedtemporary+boundedreplace retries and removedduplicatefinalsave;2writer+3journaltests pass, same48case frozenassessment nowcompletes. No ACL/admin/security changes.



Freshv2USERplan/sourcepins/preflight ready, originalattemptpreserved. SAME4runs4096steps/240seach/960stotal/1800sinclusive, fullgates/best/replays unchanged. NO TRAINING BY ASSISTANT/v2outputsabsent. #8/#15OPEN; no new performanceverdict or promotion. Source/docs localmohammad/no push.



# Awaiting runtime-run terminal evidence — 6 November 2026



User saysdone, but expected new output/results directories absent locally, no Pythonprocess observed. Exact no-learningpreflightpasses. [Evidence/limits](../docs/training/runtime-run-return-check-2026-11-06/README.md), T81. No new outcome or failure inferred; terminal output/machine/project needed. No training/source/plan/budget change by assistant. Previous readiness/history below stays historical.



# Runtime repair ready for USER comparison — 6 November 2026



[Profile/fault checks](../docs/training/runtime-profile-2026-11-06/README.md), [newmanualplan](../docs/training/runtime-repair-preparation-2026-11-06/README.md), T80. Frozenprofile41.37s/90scap; algebra/timing33.68s/60scap,0updates. Factorizedcontextweights/outputgradient algebraequivalent,72realgreedychoicesmatch within9.54e-7logiterror; batchedforward+backward1.12–1.25×throughput sample, noisy/notendtoendclaim. Durablejournals now preservecompletedcases ontimeout/predict/cleanup failure.



NewUSER-only4pairedruns same4096steps,240slearncall each/960stotal/1800sinclusive. Moretimeheadroom, notmorepractice;12balancedfit bestscreens every2048 vs48/1024, fullfinalgatesunchanged. Samefastcomputationbotharms, phase/screen timing, percaseassessmentjournals,bestzip+exactreplay kept.6unitchecks/endtoendnewsave/replay/journal and preflightpass; NO TRAINING STARTED/output/resultsabsent. #8/#15OPEN, previouscomparisoninconclusive; no sourcepush/promotion/finalmaps. Screenshotfeedback0trips/isolatedroads acknowledged, nofullgameclaim.



# Relative-position comparison INCONCLUSIVE — 6 November 2026



[Partial run and verified best replays](../docs/training/relation-comparison-review-2026-11-06/README.md), T79. USERrun stopped at per-run recording-screen deadline: baseline101/202complete4096steps, failfinalgates; relation101savedpartial2048steps/128epochs, relation202notstarted.294.23sinsidelearncalls/400.28sinclusive. Newmodel result incomplete, not a completed architecture failure; exact screening/optimizer time breakdown missing. No extension/retry/new training.



Best savingworked: baselinebest2048fit19/48,baseline202best1024fit11/48,relation101best1024fit19/48. Allhashes/finiteweights/3nativeexactreplaysPASS; partialcheckpointfinite; baselinefinalparams bit-identical topreviousrun.528best frozen assessments completed;180sreview cap stopped finalpartialprobe, percase reviewrows notretained, aggregates preserved. #8/#15OPEN,no winner/promotion. Next PROPOSED timing/profile+durable reviewprogress before further training/code changes. Candidate watchcommand inarchive; source/docslocalmohammad,no push.



# Relative-position comparison ready for USER execution — 6 November 2026



[Matched experiment, checks and command](../docs/training/relation-comparison-preparation-2026-11-06/README.md), T78. Newopt-in learned relativegoal/cursor inputs (576extra parameters), no routes/priors/mask orrewardchange. Baseline/candidate initial actor AND critic match atbothseeds, freshoptimizer/counters; newcolumns zero yet receivegradients, reload/erasedgoals checks pass.4focused+saver tests, mutation guards, realcheckpoint/native replay and no-learning preflightpass.



USER-only4runs baseline/relation×101/202,4096stepsor120s each,480strainingcall/600sinclusive; best/replay screens countedwithinbudget. Existing112fixtures/seeded assessments, final deterministic bothseed90%fit/80%layout/90%line gate unchanged. Fit-only deterministicbest selection at0/every1024/final, versionedcheckpoint+watchablereplay; finalgate separate. NO TRAINING STARTED/output/resultsabsent; source/docs localonmohammad, no push/promotion/finalmaps. #8/#15OPEN, priorfailuresunchanged.



# Sampled reliability checked; best recording support ready — 6 November 2026



[Probe and watchable preview](../docs/training/sampled-reliability-2026-11-06/README.md), T77.1024frozen episodes89.44s under180s,0updates/rejections. Five-stream layoutsuccess79.17/87.92%, only17/24 of48cases succeedall5; erased12.92/17.08%, sampledlines100%both. Original deterministicgate remainsFAILED; no promotion. Sampling useful, still inconsistent and redundant.



User asks NEXT run save best towatch (decision049). Addedopt-in pairedcheckpoint/replay saver and recorded runner with fit-only fixed screens, every1024+initial/final, tiesearlier;2tests/preflightpass. No persistent next-run plan or training issued. Currentseed101 shortfitdemo native-replayPASS, output/training/varied-extension-watch-preview-2026-11-06/best-replay.json;2seconds includes suppliedprefix+actorcompletion, notfullgame. Userwatch command inarchive. #8/#15OPEN; next remedy undecided. Alltraining USER-launched; local source/no push.



# Varied extension run reviewed: gate FAILED — 6 November 2026



[Verified result and initial sampled baseline](../docs/training/varied-extension-review-2026-11-06/README.md), T76. USER-run two4096selection pilots finish140.40slearning/230.20sinclusive, no caps/errors. Both fail deterministicfit/layout gate: fit20.83/10.42%, layout20.83/6.25%; line100%both, full-detour0%both. Sampled fit93.75%both, layout87.5/85.42%, longer100/87.5%. Fixed-stream initial sampled layout50/43.75%, so sampled completion improves, but multi-stream reliability unknown.448final episodes exactly reproduced +224posthoc frozen initial-sampled baseline; no review learning, hashes/checks verified.



#8/#15 OPEN, no promotion or relaxed gate. Next PROPOSED only: bounded frozen multi-stream sampled consistency/cost and erased-goal checks before choosing execution-policy/representation remedy. No new lesson/model/algorithm/training command or run. User gets advance change notice and launches all training. Local source/docs, no push; weights local-only. Historical preparation below stays historical.



# Varied extension pilot ready for USER execution — 6 November 2026



[Fixtures, checks and manual command](../docs/training/varied-extension-preparation-2026-11-06/README.md), T75. Opt-in balanced fixture lesson:48fit states on1000–1002,48same-length/layout-transfer on1003–1004,16longer-leg on1005; both orientations, fit lengths1–3 vs extra4. These maps are legacy exposed training maps, not fresh/final tests. First singlemap attempt insufficient, preserved;1516broader candidates,112selected physical witness completions,4dedicatedtests and no-training preflight pass.



USER command ready for2warm seeds,4096selections/120s each,240slearning/360sinclusive. Matching starter edge actors, fresh value/optimizer/counters; source prior4096steps separate. Bothseeds90%fit/80%layouttransfer/90%line deterministic required; sampled/length4 diagnostic only. No training started/output/results absent. #8/#15 OPEN; no planner, simulator/game reward/NN change or promotion. Fixtures/schema versioned, old evidence unchanged. Source/docs local mohammad, no push.



# Frozen action diagnosis completed — 6 November 2026



[Unique-fixture action diagnosis](../docs/training/network-action-diagnosis-2026-11-06/README.md), T74. All504 inference episodes finish in52.24s under180s cap,0updates/rejections; model hashes unchanged. Warm unique-held deterministic26/50 each versus sampled45/50 and32/50 (one attempt/state). Useful alternatives exist but unstable acrossseeds; original gate remainsFAILED. Many redundant strokes; cancel removal alone cannot fix warm failures. Fit missingleg lengths1–3; held length4 has6states, both warm greedy1/6. Other lengths also fail; geometry/map confounded.



Next PROPOSED only: versioned stratified fixture coverage and separate interpolation/extrapolation checks, validate before another bounded USER-run comparison. No lesson/model/reward/algorithm/budget change or new training command. #8/#15 OPEN; explain lesson edits before implementation. Records local on mohammad, no source push/promotion.



# Network-extension run reviewed — 6 November 2026



[Verified results and failure traces](../docs/training/network-extension-review-2026-11-06/README.md), T73. USER-run four4096-selection runs completed in197.95s learning/291.25s inclusive. Neither arm passes unchanged gates: scratch fit/held0%; actor-warm fit81.25/98.4375%, held48.4375/51.5625%; both warm retain100% lines, full detour9.375/34.375%. All512 fit/held records reproduced exactly without learning, plus256 traced held episodes; source/plan/build/source-model hashes and4 protected checkpoints verified. Repetition/cancellation observed, not a proven root cause. Small exposed1000/2000 fixtures,35 unique states in64 held samples; no independent final-map claim.



#8/#15 stay OPEN. Next PROPOSED only: frozen probability/sampled-action and unique-fixture diagnosis before lesson changes; no new lesson, algorithm, reward, budget, training command or training started. User requires notice before changes and launches every training session. Source/docs remain local on mohammad; no push or promotion. Historical preparation below remains historical.



# Network-extension pilot prepared for USER execution - 4 November 2026



Next#8 lessons/source/command ready: [preparation/probes/plan](../docs/training/network-lesson-preparation-2026-11-04/README.md), T72. Frozen edge policies solve longer straight lines100% (bothseeds,32fit/32held), but partial detours0%fit/31.25%held and full detours0%fit/3.125%held (canonical) remain weak. Only inference ran. New actual-command goal-connectivity lessons continue across multiple strokes,18 observed selections, no suggested waypoint; natural building obstacle, all-visible-site draw/wait. One partial initial leg is explicit scaffold for extend, not full detour skill.



5fixture+2transfer/runner checks and preflight pass. User command prepares four runs: scratch/actor-warm×101/202,4096steps or120s each,8min learning/10min inclusive. Fresh value head/optimizer/counters on warm transfer; old actor sources and4 protected hashes unchanged. Warm prior4096steps accounted separately. Train extend only, assess line retention/full-detour separately; no automatic extensions/promotion. NOT STARTED: output/results absent. User launches ALL training. #8 staysOPEN; current laptop source local/uncommitted, no push or simulator change.



# Two starter construction lessons passed - 4 November 2026



User-run approved pilot completed: [verified review and limits](../docs/training/direct-manual-review-2026-11-04/README.md), T71. Tile and single-edge marked-goal lessons each100% fit/withheld64cases in both101/202 seeds. Four separate lesson policies, not a combined autonomous city player.16384 selections,246.16s learning/275.82s inclusive, normal completion within budget; no rejections. Independent inference-only review reproduces all512 fit/withheld episode records, fresh initialization/metadata/deltas/finite parameters and preserved checkpoint hashes. Post-hoc widening to84 eligible sites also64/64 for all4 models, with goals/tools/short horizon unchanged. Four protected hybrid hashes unchanged.



#8 remainsOPEN: accept only these starter skills; multi-stroke/obstacles/color/service/stock/queues/redesign/combined unrestricted behavior unproved. Next prepare broader construction fixtures/held-out contracts before another training command. User launches ALL training; no further training started/scheduled by review. Current source/measurement copies archived; executed training source wasn't snapshotted at launch, trajectory provenance limited. No new/reserved/final maps or game checkpoint promotion. Local uncommitted work.



# Awaiting user-run classroom pilot - 4 November 2026



User approved the8min learning/10min inclusive classroom pilot and requires terminal commands for ALL training sessions; user starts them and returns results (decision047/T70, AGENTS). [Exact command and approved plan](../docs/training/direct-manual-pilot-2026-11-04/README.md). Fresh output direct-classroom-user-2026-11-04; expected results docs/training/direct-manual-pilot-2026-11-04/results/. Plan/syntax/runtime paths/fresh outputs verified only; NO TRAINING STARTED, no new outcomes. #8 remains open awaiting user execution; prior short failures remain unchanged. Latest source/plan local to laptop, not yet committed/pushed to PC.

# Direct classroom pilot partial/failed - 4 November 2026



#8 remains OPEN: [four real-command lesson runs and proposed next budget](../docs/training/direct-learnability-2026-11-04/README.md), T68–T69. Tile held-out success75%/92.19% (1/2 seeds passes); edge57.81%/71.88% (0/2 passes). Restricted marked-goal2/3-site lessons, not independent network planning or full-game scores.2048 selections,35.50s learning/70.31s pilot wall; all reloads/finite updates/host legality checks pass. Explicit cancel defect fixed before learning, actionv3;14direct+4lesson tests pass. Old direct features numerically unchanged by subclass refactor; old v2 results stay historical. Four protected hashes unchanged; only exposed1000/2000, no full-game/new/reserved/final training.



User requires notice BEFORE longer training: decision046/AGENTS. Proposed follow-up is4096steps or120s per task/seed,4runs,8min learning/10min inclusive max. NOT STARTED; no automatic extension. Same finite thresholds, fresh separate output. Need discuss before execution; #8 gate still fails and broader construction lessons remain. Weights local-only; no job running, no commit/push.



# Direct construction interface milestone - 4 November 2026



Issue#7 bounded prototype/audit complete: [contracts, fixes and evidence](../docs/training/direct-control-audit-2026-11-04/README.md), T67. New DirectEnv/DirectPolicy let the model select tools/cells with no router or strategic action priors. Existing primitive/hybrid code preserved. Versioned62-channel load/topology observation, cursor-aware shared actor/critic, per-selection gamma.99 shaping/scale.01, next-input/mask/cursor snapshots. Initial3-map random trials394 selections/180commands found6 admitted rejected draws; reasons replayed, feasibility precheck excludes all6. Corrected/final trials388 selections/180commands,0 rejections; all388 input/mask/reward records reproduce on final source and3 C# replays verify. These are controls tests, not learned gameplay (scores0).



13 focused tests pass, including normal stock road/removal/refund/upgrade, mocked13-tool decoding, log-prob/mask consistency, actor/critic/cursor dependencies, reward/end/cap and stale-cache handling. No optimizer updates, checkpoint promotion or new/reserved/final scenarios. Full all-tool/bridge-span/refund/roundabout/rail/motorway safety remains#17; masks intentionally conservative and exclude partial strokes. Next#8: direct-compatible runner and actual small construction lessons under fixed budgets, not the hybrid trainer. No direct learning pass yet; earlier hybrid synthetic failure stays historical/failed. Four protected hashes unchanged. Workmohammad; local uncommitted changes, no push.



# User direction: direct model-controlled construction - 3 November 2026



The target is now planner-free learned tool/cell control: [roadmap v3](../docs/training/learning-roadmap-v3-2026-11-03/README.md), decision045/T63. User rejects the planner-led approach. Preserve old hybrid only as comparison baseline; no further route-proposal optimization as primary path. Next#7 audits existing primitive/all-tools adapter and versions direct observation/action/cursor/mask/timing contracts; #8 proves real small construction lessons, then#10 learner choice and#15 staged traffic/repair. Optional offline teaching#9/#12 no longer blocks core progression. Closed audits/failed overnight gate remain historical, not a new direct-control pass. No code/reward/checkpoint behavior changed, no training launched. Workmohammad; GitHub updated, code/docs local uncommitted.



# Independent preparation and failed learnability gate - 3 November 2026



User authorized independent useful work overnight. [Results, source, checks and next repair](../docs/training/overnight-preparation-2026-11-03/README.md), T59–T62. #6 comparison completed: keep contextual scratch as experimental candidate, no promotion; warm showed no final task-accuracy advantage. #7 remains open:68 snapshot audit finds7 duplicate identities and904 entirely connected planned strokes; four exposed2004 prefix branches confirm one compact route2→1 commands, same final topology/stock, no branch rejections. Draft not enabled and full safety/selector comparison pending. New fresh-only registered trainer validates architecture/splits/RNG/return/budgets and preserves legacy trainer; dry-run/mocked checks only, no real new-map screening.



Seven mixed synthetic PPO runs4096 steps each: contextual scratch/warm5/6 rules, legacy4/6; ALL fail stock-conditioned upgrade gate. Two isolated runs both fit but only1/2 transfers; supervised representability probe100% fit/withheld does not repair PPO. Total36864 synthetic PPO interactions,1152 SB3 epoch counters plus200 supervised Adam steps; no full-game learning, no new/reserved/final scenarios, all4 protected hashes unchanged. Twelve focused/regression tests pass. #8 stays OPEN/failed; no tournament or long run. Next: version varied-cue diagnostic data/balanced sampling, repeat fixed isolated/mixed gate; complete#7 safety/coverage/frozen-control work. Experimental weights local-only, no background jobs, no commit/push.



# Contextual representation candidate - 3 November 2026



Issue#6 structural work implemented, acceptance still OPEN: [specification, checks and candidate](../docs/training/representation-audit-2026-11-03/README.md), T58. New opt-in contextual-candidate-actor-critic-v1 for unchanged v4 inputs gives detailed signals to critic and wider context to route/light scorers. Three focused test groups pass;68 frozen snapshots cross-scored at scratch/partial-warm initialization (not learned performance). No host/game/optimizer steps. Existing policy/trainer/reward unchanged,4 checkpoint hashes verified. Missing directed topology/provider-load distinctions documented; graph/history not selected. Keep candidate for #8 controlled learning comparison; do not promote or silently resume. #6 remains open for that gate; next actionable step#7 proposal/action audit. No long run authorized, no commit/push.



# Return/credit audit complete - 3 November 2026



Issue#5 completed with a justified no-change decision: [contract and executable evidence](../docs/training/return-audit-2026-11-03/README.md), T57. Retain gamma=.99 per macro, lambda=.99 and external-cap bootstrap for the continuing surrogate; evaluation remains actual capped trips. Twelve transition/event checks,12 buffer fixtures and2 toy timeout collection checks pass. Eleven archived trajectories rescored; no strict paired score-order reversal under legacy or illustrative time discount. Durations .45–18s and grouping bias remain limitations, not evidence of a gameplay fix. No simulator games, real checkpoint loads or optimizer updates; all four weight hashes unchanged. Next#6 context,then#7 proposals; new return schemas require consistent targets/shaping/cap semantics before#8 training readiness. No long run authorized.



# Failure corpus and causal diagnosis - 3 November 2026



Issue#4 completed: [corpus and ranked findings](../docs/training/failure-corpus-2026-11-03/README.md), T56. Ten frozen exposed2000–2004 trajectories reproduce incumbent239.0/rollback236.4;1763 decisions,68 complete event/final snapshots. One forced connection alternative at308s on2004 raises unchanged incumbent343→366 (+23), below full rollback382; total downstream effect on one diagnostic map, not a universal rule.25/56 pressured states allow only wait despite road stock; benefit of expanding proposals unmeasured. No strict score/discounted-return reversal in these pairs; discounted potential cancels at true failure. Prioritize strategic ranking/context and recovery proposals; macro-return objective remains next gate#5. Both checkpoint files/tensors unchanged,0 optimizer updates, no new/reserved collections or checkpoint promotion. Historical upgrade/light interventions remain older-policy evidence. No new long run authorized.



# Scoped simulator/environment sign-off - 3 November 2026



Issue#14 completed with limited internal-consistency scope: [audit/evidence](../docs/training/fidelity-audit-2026-11-03/README.md), T55. Fresh host build,42 mixed simulator suites,21 existing Python checks and5 additional v4 contract groups passed. Ordinary-stock light replay exact; current train/eval observations/masks and reward-scale/game equivalence checked. No optimizer updates or new/reserved-map policy benchmark. `exactReplicaValidated=false`; commercial-game parity remains unverified, trainer seed/split readiness still blocks new-protocol training (#8), macro return design remains #5 and model/action limits #6/#7/#17. Checkpoint identities unchanged. Next#4 failure corpus; no new long run authorized.



# Evaluation contract established - 2 November 2026



Issue#3 planning complete: [contract, seed registry and commands](../docs/training/evaluation-contract-2026-11-02/README.md), T54.30 development maps20000–20029,20 teacher-validation21000–21019,100 final-quarantine30000–30099; new training pool10000–19999. No new scenarios generated. Legacy8000–8009 remains reserved for its prior upgrade comparison. Defined mean/uncertainty/median/tail/error/resource gates, independent RNG roles and bounded screening limits; no new run authorization. Current trainer needs configurable splits/RNG/validation before comparative training (issue#8); release-report implementation remains issue#13. Next is issue#14 fidelity. Baseline/checkpoints below unchanged; tracker#1 remains open.



# Baseline established - 2 November 2026



Completed issue#2's read-only run assessment. [Baseline registry and evidence](../docs/training/baseline-review-2026-11-02/README.md), T53. Provisional development incumbent: `output/training/upgrades-night-01/validation-best.zip`, supported-upgrades ON,239.0 on exposed2000–2004. Same-contract rollback/control: `initial.zip`,236.4. Preserve original unfiltered protected model228.0 and all hashed files. Selected gain+2.6/+1.10%,2 wins/1 tie/2 losses; final213.4 not promoted. Seven validations, saved source/tensors/optimizer and824 episode/monitor counts checked; no new inference/games or learning. No unseen-map improvement claimed. Next: issue#3 evaluation/seed/budget contract. Tracker#1 remains open; no new training authorized/launched.



# Model-specific roadmap revision - 2 November 2026 (historical planning status)



User authorized auditing/reworking the roadmap and permits a fresh model or entirely different algorithm. [Live tracker #1](https://github.com/JoeJaffal/mini_motorways/issues/1) now contains19 open child issues; [v2 plan](../docs/training/learning-roadmap-v2-2026-11-02/README.md) supersedes v1. [Source/checkpoint/synthetic audit](../docs/training/model-audit-2026-11-02/README.md) confirms detailed signal rows do not reach critic and local light logits lack global/traffic conditioning with fixed signal rows; game-score effects unmeasured. It also identifies macro-time/return contracts, proposal/tool limits and narrow evaluation as gates before an algorithm tournament. Current PPO remains a control; imitation/memory/search are conditional. Four-hour metadata: initial236.4, selected239.0, final213.4 on five exposed maps; no new game or optimizer update. Hashes archived, but issue#2's baseline decision is still open. No new long run authorized/launched. See T52.



# Planning update - 2 November 2026 (historical v1)



User requested and authorized publishing a GitHub roadmap. [Tracker issue #1](https://github.com/JoeJaffal/mini_motorways/issues/1) links 12 open steps with closure criteria and dependencies; [durable plan](../docs/training/learning-roadmap-2026-11-02/README.md), T50. Start by reviewing the prepared four-hour run; its outcome was not inspected during planning. Teacher/imitation/correction/PPO experiments are gated proposals. No new training/evaluation was authorized or launched by this roadmap; existing run commands below remain unchanged.



# Current preparation - 31 October 2026



User chose4h training instead of more tests. Opt-in supported-upgrades integrated, checkpoint/eval/resume flag preserved; short checks only, no job launched. Resume protected checkpoint with240min/4workers; source checkpoint preserved and best guard retained. [Exact command/limits](../docs/training/supported-upgrade-training-2026-10-31/README.md), T45. Fresh8000-8009 test pending, not required before user-authorized experiment.



# Latest result - 31 October 2026



Supported-upgrade filter186.4->228.8 on5 development maps (4 wins/1 tie). Engineered improvement, concentrated on2000, not learning/generalization evidence. Prepared identical frozen comparison on8000-8009 (20 games); user runs, no job launched. Protected checkpoint/default training unchanged. [Evidence/command](../docs/training/upgrade-support-results-2026-10-31/README.md), T44.



# Latest preparation - 31 October 2026



Optional supported-upgrade rule comparison ready for user: frozen final policy,5 exposed development maps x2 conditions. Offer information already visible; filter only unsupported-extra packages with a supported alternative/no fewer roads. Training defaults unchanged. Synthetic checks and short smoke passed; full evaluation pending. [Command/protocol](../docs/training/upgrade-support-test-preparation-2026-10-31/README.md), T43.



# Latest result - 31 October 2026



Single first-upgrade intervention recovered final policy83->266 trips on2000, two lights placed autonomously, unchanged weights. This is a total causal effect on one exposed development map, not generalization or isolated light physics. Keep protected checkpoint; investigate upgrade representation/utility before long training. No new job launched. [Evidence](../docs/training/first-upgrade-results-2026-10-31/README.md), T42.



# Latest preparation - 31 October 2026



First-upgrade intervention CLI ready: frozen final baseline versus override only at140s on2000, then normal policy. Short wiring smoke passed; does not reach intervention. User runs full test; no training or full evaluation started. [Command/protocol](../docs/training/first-upgrade-test-preparation-2026-10-31/README.md), T41.



# Latest diagnosis - 31 October 2026



Seed2000 reproduced235 vs83. First divergence is upgrade at140s: protected gets2 lights, final another package. Final builds no lights and dies with crossing queues; later route/wait differences also exist. Causality unproven. Next recommendation: force only first upgrade in frozen final policy, then normal decisions. No job launched. [Evidence](../docs/training/regression-2000-2026-10-31/README.md), T40.



# Training status - 31 October 2026



Prepared user-run seed2000 frozen protected-versus-final diagnostic after continuation regression. Short two-second wiring check passed; full comparison pending, no training started. See T39 and [command/limits](../docs/training/regression-diagnostic-preparation-2026-10-31/README.md).



# Training status - 30 October 2026







Latest: signals-context-02 completed two hours/370 games. Development mean228.0 ->186.4; all periodic checks below starting baseline. Protected validation-best remains the starting228.0 policy. Best training480 is not evidence of improvement. Recommendation: pause long training and diagnose regression on development maps. No job launched. See T38 and [evidence](../docs/training/signal-context-continuation-2026-10-30/README.md).







Earlier status entries below are historical.







V4 light-availability test complete: ON177.5 vs OFF159.1 (+11.6%), three wins/



six ties/one loss on seeds7000-7009. Light actions help this policy's mean on



this set but can still hurt individual maps. Next recommendation is a user-run



two-hour continuation of the same checkpoint/settings, not another architecture



change. No job started. See T37 and



[paired evidence](../docs/training/signal-context-light-results-2026-10-30/README.md).







Next prepared diagnostic: v4 light placement ON/OFF on seeds7000-7009, same



selected228.0-development model, twenty frozen games. User execution pending;



no assistant-run simulation/training. Exact command in TRAFFIC_LIGHT_TEST.md.







V4 fresh-map test complete: deterministic175.9->194.0 (+10.3%), two maps better,



five tied, three worse. Sampled168.7->169.0, nine ties/one+3 gain. Thus additional



learning has an inconsistent point-average benefit, not established broad



improvement or a proven light-placement fix. Forty frozen games, seeds6000-6009;



no further jobs started. See



[full scores and limits](../docs/training/signal-context-fresh-2026-10-30/README.md), T35.







V4 one-hour user trial completed normally: 167 games, validation204.2 ->228.0



(+11.7%), with most gain on one of five maps. Best selected checkpoint is local



output/training/signals-context-01/validation-best.zip. No trainer active.



Next: user-run frozen comparison on new seeds6000-6009; no additional training



or full evaluation launched by the assistant. See SIGNAL_CONTEXT.md and T34.







V4 signal context is prepared: queue causes and current destination pressure,



with a v3->v4 weight-preserving warm start and fresh optimizer. Four short checks



and a tiny no-update CLI wiring smoke passed; no learning benefit is established.



Per user preference, no long job was started/waited on. Use the



[manual one-hour command](SIGNAL_CONTEXT.md), then report completion for analysis.







Seed5009 diagnosis complete: the lights interact. With the ON construction



schedule fixed, both lights score279, first-only374, second-only277, neither276.



The full OFF policy's different command schedule scores475. The second light



was placed by a parking-access queue; current light inputs lack queue-cause



information. This is a diagnostic/input-gap finding, not a trained fix or a



reason to ban all lights. No model/rules/reward changed. See



[evidence and limits](../docs/training/light-failure-5009-2026-10-29/README.md), T32.







Traffic-light ON/OFF test is now complete: ON190.9 vs OFF209.9 mean trips, with



2 wins/5 ties/3 losses. The -19 mean is dominated by seed5009 (-196 trips);



the other nine net+6 for ON. This is inconsistent placement benefit for the



frozen policy, not proof that lights universally harm simulator traffic. See



[paired evidence](../docs/training/light-availability-2026-10-29/README.md), T31.



No new training was started. The preparation note below is historical.







Next diagnostic prepared: [traffic-light ON/OFF comparison](TRAFFIC_LIGHT_TEST.md),



same frozen trained policy on ten paired seeds. Full comparison not started;



only a short startup smoke and mask/observation checks have passed. This is an



evaluation command, not authorization to start more training.







**Fresh-map test complete:** the preselected trained model improved deterministic



mean 161.3 -> 207.4 (+28.6%) on unseen LosAngeles seeds4000-4009, winning9/10.



Secondary sampled mean182.0 -> 188.9 (+3.8%); five wins/two ties/three losses,



with nearly all aggregate gain on one map. This supports deterministic transfer



but remains a ten-map/one-model test with weak sampled evidence. All40 games



were inference only; frozen selection/weights preserved, no retuning. See



[paired results and evidence](../docs/training/signals-fresh-2026-10-29/README.md)



and T27. No training is active; selected local weights remain



`output/training/signals-night-01/validation-best.zip`.







**Latest: user overnight run stopped early, cause unknown.** `signals-night-01`



has no active trainer, final checkpoint or summary; last unfinished status is



4h18m/8h,832 games. Saved best validation mean improved167.4->204.2 (+22%),



latest validation185.4, best completed training recording494 trips on seed1099.



The trained validation-best checkpoint beat its starting policy; the later



fresh-seed result is recorded above. Existing checkpoints are retained locally.



See [raw evidence](../docs/training/signals-overnight-2026-10-29/README.md) and T26.







The following preparation record predates the user-started overnight run.







Traffic-light **v3 is ready for a fresh overnight experiment**, not yet run.



It adds normal-stock legal junction proposals, existing-light observations and



traffic/global context for route choices. Starting-prior temperature 2 permits



more varied sampling; it is not a proven performance improvement. Two controlled



512-decision pilots both regressed slightly (122.67 -> 122.33 mean on three dev



maps), so both retained the starting model as validation best. Baseline/tie



protection now prevents a worse first validation from being selected. The full



overnight run is stopped/not launched. See [command and contract](SIGNALS.md),



[archived audit/pilots](../docs/training/signals-2026-10-29/README.md) and history T25.







Earlier v2 and investigation results below remain historical; old weights and



PDFs were not overwritten.







Latest user-started v2 trials: `congestion-v2-01` and `-02` each finished a



30-minute fresh run (neither resumed). Both recorded **432 trips** on seed 1099.



Development mean started at 167.0 and ended at 142.4/142.2 respectively; best



periodic validation was 167.4 for both. This is no reliable learning gain and



final policies regressed. Both are stopped. See history T24 and the



[two-run assessment](../docs/training/congestion-v2-2026-10-28/two-user-runs.json).



The older investigation results below remain historical.







The authorized investigation is complete. All training and frozen evaluation



have stopped; no recurring run is scheduled. Work is on `mohammad`; `main` remains



the playground. Existing checkpoints and historical PDFs are preserved.







Post-investigation correction: planner-aided candidate traffic and waiting now



refresh at every decision rather than only when route geometry is rebuilt.



Five goal-agent checks pass, including a new fixed-topology traffic regression.



No new performance evaluation or training was started; the scores below and PDF



describe the historical implementation. See history T21 for scope and limits.







The optional congestion v2 model is now ready for a controlled fresh-model trial:



live traffic grid, junction/route load summaries and physical bypass proposals.



Eight goal checks pass, including actual bypass replay and v2 actor/CNN updates



and save/reload. Four-worker startup and frozen evaluator checks passed. A tiny



startup smoke stopped before an optimizer update; it is not performance evidence.



The three-map frozen comparison is mixed (120.3 -> 123.3 mean, two maps worse),



so no reliable gameplay gain is claimed. No long training was started. See



[training command and limits](GOAL_AGENT.md) and history T22. Existing reports



and the 356-trip recording remain historical v1 results.







**Best recordings:** 126 trips for the primitive all-tools policy; **356 trips**



for the new planner-aided goal agent (seed 1075, 971.65 simulated seconds,



972 ordinary commands, normal failure). Both checked exactly in the native game;



the 356-trip recording also passed headless verification. The 1,000-trip target



has not been reached.







**Learning evidence is limited.** Most improvement comes from engineered action



priors and route planning. The trained goal candidate improved one of ten fresh



deterministic maps; sampled evaluation tied its starting policy. A high training



best does not establish reliable learning or make that final checkpoint the best.







See the [new 10-page report](../docs/training/model-investigation-2026-10-28.pdf),



[full protocol and findings](EXPERIMENT_2026_10_28.md),



[chronological history](EXPERIMENT_HISTORY.md) and



[archived evidence](../docs/training/investigation-2026-10-28/README.md).







## Fresh-map comparison







Selection was frozen using development seeds 2000-2004 before opening final



seeds 3000-3009. Each policy used normal finite OriginalReference materials and



failure rules, a 3,600-second external cap, and no optimizer updates.







| Frozen policy | Deterministic mean trips | Best |



| --- | --- | --- |



| Earlier stopped primitive policy | 0.6 | 4 |



| Informed primitive starting policy | 23.4 | 93 |



| Development-selected trained primitive | 20.7 | 92 |



| Goal policy: frozen informed initial | 119.1 | 270 |



| Goal policy: selected trained candidate | 125.7 | 270 |







The goal-policy gain is entirely seed 3006, from 56 to 122 trips; nine maps tied.



Secondary sampled inference averaged **130.4 for both** policies, using one



trajectory per map and Torch seed 43 plus scenario offset, reset per game.



Ten maps and one training replicate do not establish robust generalization.



No test result triggered further training or checkpoint selection.







## What changed







The original 450,610-parameter, 50-channel all-tools model remains available.



Opt-in connectivity inputs add two channels (450,898 parameters). Explicit



adaptation preserves starting action probabilities by zero-filling new weights.



Spatial residual scoring, informed endpoint priors, conservative productive-draw



masks, no-op diagnostics and longer PPO credit windows were tested separately.



Primitive pilots did not establish a strong learning improvement.







The **separate goal agent has 10,334 parameters**. It selects among visible



matching-color connection proposals; a deterministic router executes ordinary



road/bridge strokes. It also waits and chooses upgrades. It excludes motorways,



roundabouts, traffic lights, demolition and manual driveway edits. Its starting



prior is engineered, not learned. [Full inputs, restrictions and commands](GOAL_AGENT.md).







Primitive reward remains trip delta plus bounded potential shaping, gamma .999.



Goal reward uses the same bounded connection idea but gamma .99 per macro decision.



Numerical reward scale .01 changes optimization, never game score. Choice-only



mode folds forced waits into the preceding decision; it has separate timing/reward



metadata. A frozen test verified identical ordinary command histories with/without



collapsing forced waits at a 180-second cap. The saved timing mode restores at



inference. Resume inherits timing, rate and reward scale unless explicitly changed.







## Goal-agent pilots







All four started from identical policy weights and empty optimizer states, with



five-map development mean 162.6. Each had a 25-minute learner cap and two workers.



Initial/final evaluation adds time; periodic validation consumes learner time.







| Arm | Macro decisions | Games | Best training | Final dev mean |



| --- | --- | --- | --- | --- |



| Scale 1 | 9,450 | 72 | 304 | 162.6 |



| Scale .01 | 8,508 | 63 | 300 | 162.6 |



| Choice only | 2,586 | 70 | 296 | 162.6 |



| Choice + rate .001 | 3,556 | 91 | 356 | 128.0 |







The higher-rate final checkpoint regressed despite recording 356 trips in one



training game. Operational selection conservatively kept the frozen initial



policy on a development tie. The trained comparison is the first goal run's



validation-best checkpoint, not the 356-trip run's final model.







Local operational baseline: `output/training/goal-hybrid-20261028/initial.zip`.



Local trained comparison: `output/training/goal-hybrid-20261028/validation-best.zip`.



Local primitive candidate: `output/training/informed-credit-20261028/validation-best.zip`.



Weights and generated binaries remain local; code, evidence and PDF are in Git.







## Watch the 356-trip recording







```powershell



cd C:\Users\moham\mini_motorways



.\.venv\Scripts\python.exe .\training\watch_best.py --run output/training/goal-rate-20261028



```







Add `--play` to begin paused at the start. The native viewer labels planner-aided



replays. This exact action history can span policy updates and sampled actions;



a checkpoint saved at episode end is only a snapshot, not a guarantee of replaying



the same score. For a future bounded experiment, use [the goal guide](GOAL_AGENT.md)



or [the primitive quickstart](QUICKSTART.md), with a fresh output folder.







## Verification and remaining limits







Checks passed: 42 shared simulator suites; ten five-map protocol runs; 31 Python



checks across environment, rewards, workflow, parallel, shutdown, feature/migration,



draw-mask and goal-adapter suites. Four-worker resume restored .01 scale and



choice-only timing without a weight update. Repeated sampled inference produced



identical metric/action records. Frozen evaluations verified unchanged weights.



The OriginalReference native player rebuilt successfully; generated scene/settings



noise was restored. Reports record command corrections and evidence compaction.







The primitive draw-noop metric means unchanged infrastructure/connection arrays;



it is not proof of no driveway-only or pending-removal change. The goal router



avoids parcels/demolition but redraws reused paths: 438/668 initial-development



draws made no network change. Removing those strokes and offering capacity-aware



route alternatives are future executor experiments, not implemented gains.



Game duration, routing and serialization explain throughput; there is no artificial



0.8-games/second cap. More games or a higher training mean alone is not success.







OriginalReference remains a reconstruction. These results do not demonstrate



commercial-game fidelity, other-city transfer or a reliable 1,000-trip policy.



The earlier 12-page report is a historical pre-investigation snapshot.





Gameplay fidelity investigation (8 November 2026): [checks-only report](../docs/training/gameplay-fidelity-check-2026-11-08/README.md). Material parking/supply differences found; original difficulty parity unvalidated. No gameplay fix, training or model promotion. Prior learning status remains unchanged.



Road-scarcity follow-up: [accounting checks](../docs/training/gameplay-fidelity-check-2026-11-08/ROAD_STOCK.md) found base-price mismatch and roundabout conversion road loss. Checks only; no implementation or learning change.



Roundabout fidelity follow-up: [priority/topology findings](../docs/training/gameplay-fidelity-check-2026-11-08/ROUNDABOUTS.md); no gameplay/learning changes, score impact unresolved.



First fidelity repair (8 November): [roundabout concrete conservation](../docs/training/roundabout-concrete-fix-2026-11-08/README.md),44 suites PASS; source/headless fixed, running player remains old build. No training/promotion; other fidelity fixes open. Future video comparison must distinguish reconstructed layout/actions from validated same-seed parity.

