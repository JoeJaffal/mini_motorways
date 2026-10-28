"""Build the completed investigation report from archived evidence, no simulator."""
from pathlib import Path
import hashlib
import json
import shutil
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
DATA=BASE/'investigation-2026-10-28';FIG=DATA/'figures';FIG.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/pdf/three_hour_model_investigation.pdf';OUT.parent.mkdir(parents=True,exist_ok=True)
assessment=json.loads((DATA/'assessment.json').read_text())
selection=json.loads((DATA/'experiments/selection.json').read_text())
runs={p.parent.name:json.loads(p.read_text()) for p in (DATA/'runs').glob('*/summary.json')}
tests={p.stem:json.loads(p.read_text()) for p in (DATA/'experiments/final-tests').glob('*.json') if 'replay' not in p.stem}
INK='#183342';TEAL='#087F83';GOLD='#B55C17';GREY='#586F7D'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
styles=getSampleStyleSheet()
for name,font,size,leading,color in [('Body','Arial',10,14.5,INK),('Title','Arial-Bold',27,31,INK),
        ('Heading','Arial-Bold',14,19,TEAL),('Small','Arial',8.3,11.5,GREY),('Cell','Arial',8.8,12,INK)]:
    styles.add(ParagraphStyle(name='Inv'+name,fontName=font,fontSize=size,leading=leading,
                             textColor=colors.HexColor(color),spaceAfter=9))
W=487;story=[]
def p(text,style='Body'):story.append(Paragraph(text,styles['Inv'+style]))
def heading(text):p(text,'Heading')
def page(title,sub=None):
    if story:story.append(PageBreak())
    p(title,'Title')
    if sub:p(sub)
def table(headers,rows,widths=None):
    data=[[Paragraph(str(v),styles['InvCell']) for v in row] for row in [headers]+rows]
    t=Table(data,colWidths=widths or [W/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEEEF')),('VALIGN',(0,0),(-1,-1),'TOP'),
      ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),
      ('BOTTOMPADDING',(0,0),(-1,-1),6),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F6')])]))
    story.append(t);story.append(Spacer(1,9))
def figure(name):
    from PIL import Image as PILImage
    path=FIG/name
    with PILImage.open(path) as im:h=W*im.height/im.width
    story.append(Image(str(path),width=W,height=h));story.append(Spacer(1,8))
def note(s):p(s,'Small')
def mean(rows):return statistics.mean(r['trips'] for r in rows) if rows else 0
def savefig(name):plt.savefig(FIG/name,dpi=170);plt.close()
def lines(name):
    path=DATA/'runs'/name/'validation.jsonl'
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

pilots=[('Legacy control','pilot-control-20261028'),('Connectivity inputs','pilot-features-20261028'),
        ('Spatial residual','pilot-spatial-20261028'),('Productive draw mask','pilot-productive-20261028')]
fig,ax=plt.subplots(figsize=(8.2,3.7),layout='constrained')
x=list(range(4));ax.bar([i-.18 for i in x],[mean(runs[n]['after']) for _,n in pilots],.34,color=TEAL,label='Final sampled')
ax.bar([i+.18 for i in x],[mean(runs[n]['deterministic_after']) for _,n in pilots],.34,color=GOLD,label='Final deterministic')
ax.set(xticks=x,xticklabels=[s.replace(' ','\n',1) for s,_ in pilots],ylabel='Mean actual trips',title='Small primitive-policy pilots did not solve transfer')
ax.legend(frameon=False);savefig('primitive-pilots.png')

fig,ax=plt.subplots(figsize=(8.2,3.5),layout='constrained')
ax.axhline(12.6,color=GREY,linestyle='--',label='Frozen informed start (12.6)')
for name,label,color in [('informed-spatial-20261028','Short credit',GOLD),('informed-credit-20261028','Longer credit',TEAL)]:
    s=runs[name];v=lines(name)
    xx=[0]+[r['policy_steps'] for r in v]+[s['policy_steps']]
    yy=[12.6]+[r['mean_trips'] for r in v]+[mean(s['deterministic_after'])]
    ax.plot(xx,yy,'o-',color=color,label=label)
ax.set(xlabel='Policy selections',ylabel='Mean actual trips',title='Development validation: informed primitive policy');ax.legend(frameon=False,fontsize=8)
savefig('primitive-validation.png')

goal_names=assessment['goal_runs'];fig,axes=plt.subplots(1,2,figsize=(8.2,3.5),layout='constrained')
for i,name in enumerate(goal_names):
    s=runs[name];v=lines(name);color=[TEAL,GOLD,'#6D598A','#4377A1'][i%4]
    axes[0].plot([0]+[r['wall_seconds']/60 for r in v]+[s['training_wall_seconds']/60],
                 [mean(s['before'])]+[r['mean_trips'] for r in v]+[mean(s['after'])],'o-',color=color,label=assessment['goal_run_labels'][name])
    path=DATA/'runs'/name/'episodes.jsonl';episodes=[json.loads(l) for l in path.read_text().splitlines()]
    scores=[r['trips'] for r in episodes]
    rolling=[statistics.mean(scores[max(0,j-19):j+1]) for j in range(len(scores))]
    axes[1].plot(range(1,len(rolling)+1),rolling,color=color)
axes[0].axhline(mean(runs[goal_names[0]]['before']),color=GREY,linestyle='--',label='Frozen initial')
axes[0].set(xlabel='Learner wall minutes (includes validation)',ylabel='Development mean trips',title='Frozen validation (5 seeds)');axes[0].legend(frameon=False,fontsize=7)
axes[1].set(xlabel='Completed training games',ylabel='Rolling mean trips (up to 20)',title='Mixed training layouts')
savefig('goal-learning.png')

fig,ax=plt.subplots(figsize=(8.2,3.8),layout='constrained')
test_order=assessment['test_order'];palette=[GREY,'#6594B0',GOLD,TEAL,'#6D598A']
for j,key in enumerate(test_order):
    r=tests[key];scores=[x['trips'] for x in r['results']]
    ax.plot(range(3000,3010),scores,marker=['o','s','^','D','x'][j%5],label=assessment['test_labels'][key],color=palette[j%len(palette)],linewidth=1.5)
ax.set(xlabel='Final test seed (never used for updates or selection)',ylabel='Actual trips',title='Ten fresh maps: paired frozen-policy comparison')
ax.set_xticks(range(3000,3010));ax.tick_params(axis='x',rotation=35);ax.legend(frameon=False,fontsize=7)
savefig('final-tests.png')

fig,ax=plt.subplots(figsize=(8.2,3.8),layout='constrained')
for offset,key,label,color in [(-.19,'goal-initial-sampled','Frozen initial',TEAL),(.19,'goal-trained-sampled','Selected trained',GOLD)]:
    ax.bar([i+offset for i in range(10)],[r['trips'] for r in tests[key]['results']],width=.36,label=label,color=color)
ax.set(xticks=list(range(10)),xticklabels=[str(i) for i in range(3000,3010)],xlabel='Fresh scenario seed',ylabel='Actual trips',title='Secondary sampled-policy comparison')
ax.tick_params(axis='x',rotation=35);ax.legend(frameon=False);savefig('sampled-tests.png')

page('Model training investigation','Authorized three-hour window | 28 October 2026 | Branch mohammad')
p(assessment['headline'],'Heading')
p(assessment['conclusion'])
table(['Measurement','Outcome'],[
    ['Best recorded primitive training game',str(assessment['primitive_best'])+' trips'],
    ['Best recorded planner-aided training game',str(assessment['goal_best'])+' trips'],
    ['Planner-aided frozen start, development mean',f"{mean(runs[goal_names[0]]['before']):.1f} trips (5 maps)"],
    ['Selected planner-aided checkpoint, development mean',f"{selection['goal']['mean_trips']:.1f} trips (5 maps)"],
    ['Target', '1,000 actual completed trips; '+assessment['target_status']],
    ['Rules','OriginalReference; normal finite materials; future schedules hidden']],[225,W-225])
heading('What counts as learning?')
p('A better hand-written prior or a pathfinder can improve scores before any training. Learning means the updated policy improves on its own frozen starting policy on separate maps. This report shows those baselines explicitly. A single impressive replay or increasing shaped reward is insufficient.')
note('The original all-tools agent remains available. The new goal agent is a separate restricted, planner-aided experiment. OriginalReference is a reconstruction, not a validated exact copy of the commercial game. Checkpoints and binaries stay local; small evidence and report sources are archived in Git.')

page('1 / What was wrong?','The main difficulty was coordinating useful road construction, not an artificial game-per-second limit.')
figure('primitive-pilots.png')
table(['Pilot','Selections','Best training','Final deterministic mean'],[
    [label,f"{runs[name]['policy_steps']:,}",runs[name]['best_training_score'],f"{mean(runs[name]['deterministic_after']):.1f}"] for label,name in pilots],[181,82,95,129])
p('The input-only pilot preserved starting action probabilities and compared against the same old weights with a fresh optimizer. Adding explicit missing connections did not establish an improvement. Early logs showed about 89% of draws made no measured change to road-tile/connection arrays, motivating endpoint diagnostics. Driveway-only changes or pending-removal cancellation are outside that metric; it is not a complete no-effect test.')
note('Five development seeds, one run per configuration. Spatial residual stopped at its 18-minute cap (63,490 selections); others reached 65,536. Sampled and deterministic policies differ. These are engineering pilots, not replicated significance tests or speed benchmarks. Shared CPU load and validation overhead affect timings.')

page('2 / Better inputs and masks','These changes help the policy understand the current map without changing the game rules.')
table(['Change','What it does / why'],[
    ['52-channel option','Adds unconnected houses and destinations without connected matching-color supply to the original 50 map channels. Binary supply is not a capacity guarantee.'],
    ['Explicit checkpoint adaptation','Copies old weights and zero-fills the new input weights; tests verify initial action probabilities match. A fresh optimizer is explicit.'],
    ['Spatial residual option','Shared per-cell scoring supplements global coordinate logits; zero initialization preserves the original starting policy.'],
    ['Productive draw mask','Removes endpoints only when a read-only simulator query proves a stroke cannot change the road network. Possible changes may still be rejected by normal rules.'],
    ['Immediate draw diagnostics','Counts unchanged road-tile/connection arrays and distinct endpoint pairs before advancing time. Other state changes are outside this measurement.'],
    ['Development checkpoints','Periodically freezes inference on seeds 2000-2004; logs actual trips and saves validation-best separately from the best training replay.']],[145,W-145])
heading('Reward remains tied to actual delivery')
p('The primitive agent uses completed-trip delta plus discounted potential shaping: reward = new trips + gamma * next potential - previous potential. Potential is 0.25 times the number of usefully connected houses, capped at eight. True game failure resets potential to zero; external time limits retain it for bootstrapping. Breaking and rebuilding a connection cannot repeatedly collect net discounted credit.')
p('All primitive tools remain exposed. Structured inputs exclude future schedules and RNG state. Cells beyond the current playable map are hidden. Every experimental input/action schema is named explicitly so incompatible checkpoints are not silently reused.')
note('Original parameters: 450,610. Connectivity inputs: 450,898. Informed spatial policy: 453,484. Parameter counts describe numerical weights, not games or rules. The original policy has no recurrent memory.')

page('3 / Informed actions and credit','A useful starting bias improved behavior, but that improvement must not be attributed to PPO.')
figure('primitive-validation.png')
p('The informed spatial variant initially favors current house-driveway endpoints, matching destination endpoints, waiting when no relevant missing supply remains, and offered upgrades. This is an engineered prior. It does not compute routes. The prior is trainable and the spatial residual can adjust cell scores.')
p('Its frozen deterministic development scores were 0, 0, 8, 33, 22: mean 12.6. The short-credit run used aggregate rollout 256 and GAE lambda 0.95. The longer-credit arm started from the exact same checkpoint, with rollout 1,024 and lambda 0.99. Both used gamma 0.999, four workers, the same reward and productive masks.')
table(['Arm','Final deterministic mean','Best training'],[
    ['Short credit',f"{mean(runs['informed-spatial-20261028']['deterministic_after']):.1f}",runs['informed-spatial-20261028']['best_training_score']],
    ['Longer credit',f"{mean(runs['informed-credit-20261028']['deterministic_after']):.1f}",runs['informed-credit-20261028']['best_training_score']]],[200,170,117])
note('Two interacting credit changes were tested together, not an isolated one-factor ablation. The runs temporarily shared eight simulator processes, so wall speeds are not comparable hardware benchmarks. Selection includes frozen initial and final checkpoints, not only periodic validation-best.')

page('4 / A separate connection agent','The neural policy chooses which connection to build; a visible-state router handles the individual strokes.')
table(['Stage','What happens'],[
    ['1. Observe','Read the current map, materials, houses, destination entrances, colors, demand, congestion and connectivity. Never read future spawns.'],
    ['2. Propose','A deterministic shortest-cost router proposes current matching house/destination connections using ordinary road tiles and available stock.'],
    ['3. Choose','Maskable PPO scores up to 512 candidate connections, two upgrade choices and waiting. Shared weights score candidate rows rather than memorizing coordinate IDs.'],
    ['4. Execute','Compress the chosen route into ordinary straight strokes. Each completed command advances normal simulation time. Waiting executes up to five ordinary one-second commands.'],
    ['5. Learn','Collect actual trip changes plus bounded potential shaping, estimate future returns, and update policy/critic weights with PPO.'],
    ['6. Check','Freeze the policy on separate development maps and compare against its own frozen initial checkpoint.']],[100,W-100])
heading('What it sees')
p('Each candidate has 25 values: home/destination coordinates and displacement, color, new-road and route costs, demand, missing home/shop supply, existing-road fraction, traffic/waiting, overcrowding, new water tiles and validity. Forty-two globals summarize materials, offers, current clock/week, trips, supply and congestion. Up to 512 candidates are supported; overflow raises an error instead of silently dropping entries.')
heading('What it cannot do in this experiment')
p('It builds road/bridge strokes, waits and chooses upgrades. Motorways, roundabouts, traffic lights, demolition and manual driveway edits are excluded. This is deliberately a different action abstraction; it does not establish that the original full-tools model learned those skills.')
note('10,334 trainable parameters. Hand-designed initial candidate scores prefer low cost, demand and missing supply. PPO learning rate 0.0001 (final rate pilot: 0.001), entropy 0.005, gamma/lambda 0.99 per macro decision, rollout 256, four epochs. Variable-duration macro actions change the discounting problem. The router is assistance, not learned route construction or an optimal planner.')

page('5 / Did the connection agent learn?','Training results and frozen validation answer different questions.')
figure('goal-learning.png')
table(['Run','Wall minutes','Macro decisions','Games','Best training','Final dev mean'],[
    [assessment['goal_run_labels'][n],f"{runs[n]['training_wall_seconds']/60:.1f}",f"{runs[n]['policy_steps']:,}",runs[n]['episodes'],runs[n]['best_training_score'],f"{mean(runs[n]['after']):.1f}"] for i,n in enumerate(goal_names)],[92,55,92,43,100,105])
p(assessment['goal_interpretation'])
heading('Why games per second changed')
p('There is no deliberate 0.8-games/second limit. Each game lasts a different number of simulated seconds and requires a different amount of routing, serialization and policy work. Better games can take longer to finish. Workers collect experience for one shared policy; they are not separate independently learning models. Path planning adds CPU work, while macro decisions reduce the number of neural choices per game.')
note('These arms start from the same initial checkpoint; they are not consecutive training stages. Scaled rewards multiply numerical learning rewards by 0.01, never actual scores. Choice-only timing folds forced waits into the preceding decision and uses a separately versioned macro reward. Its decision counts are not comparable to five-second-wait counts. Periodic validation consumes learner time; initial/final evaluation is additional. Shared CPU load and changing seed mixes limit comparisons of wall speed and training means.')

page('6 / Fresh-map final test','Candidate selection was recorded before examining seeds 3000-3009. No subsequent optimization uses these results.')
figure('final-tests.png')
table(['Frozen policy','Mean','Median','Best'],[
    [assessment['test_labels'][key],f"{tests[key]['mean_trips']:.1f}",f"{tests[key]['median_trips']:.1f}",tests[key]['best_trips']] for key in test_order],[250,79,79,79])
p(assessment['test_interpretation'])
note('Ten paired scenario seeds, deterministic inference, 3,600 simulated-second external cap, normal failure rules. Frozen model parameters were checked before/after inference and remained unchanged. Training and test city are both Los Angeles; seed separation does not establish transfer to other cities. One training replicate and ten test maps are not evidence of robust generalization or guaranteed future improvement.')

page('7 / Sampled-policy check','Small probability changes can matter even when the most likely action stays the same.')
figure('sampled-tests.png')
table(['Sampled frozen policy','Mean','Median','Best'],[
    [label,f"{tests[key]['mean_trips']:.1f}",f"{tests[key]['median_trips']:.1f}",tests[key]['best_trips']]
    for label,key in [('Initial goal','goal-initial-sampled'),('Trained goal','goal-trained-sampled')]],[250,79,79,79])
p(assessment['sampled_interpretation'])
heading('Greedy and sampled play answer different questions')
p('Deterministic evaluation always chooses the currently most likely legal action. Sampled evaluation draws an action from the policy probabilities, as training does. Neither a single sampled win nor an unchanged greedy score proves the whole learning process is successful or broken. Both should be compared against the same starting policy and separate maps.')
note('Each policy gets one sampled game on each of ten scenario seeds, with a 3,600-second cap. The requested RNG seed is applied after loading the checkpoint; reproducibility was checked by repeating a sampled development game and comparing exact ordinary-command recordings. These are inference-only tests: weights remain unchanged.')

page('8 / The best recording','A replay is an exact action history, not proof that the final checkpoint will reproduce that score.')
capture=DATA/'best-map.png'
if capture.exists():
    from PIL import Image as PILImage
    with PILImage.open(capture) as im:h=W*im.height/im.width
    story.append(Image(str(capture),width=W,height=h));story.append(Spacer(1,10))
replay=assessment['best_replay']
table(['Recorded game','Value'],[['Source',replay['source']],['Seed / actual trips',f"{replay['seed']} / {replay['score']}"],
    ['Simulated duration / ordinary commands',f"{replay['duration']:.2f}s / {len(replay['actions'])}"],
    ['Recording end','Partial at training stop' if replay.get('partial') else 'Normal failure' if replay.get('terminated') else 'External episode cap'],
    ['Verification',assessment['replay_verification']]],[220,W-220])
p('Best-game ranking uses actual trips, then survival time, then fewer rejected actions. An episode can span PPO updates and uses sampled actions during training. The exact command recording preserves that game; the checkpoint saved at its end is only a policy snapshot.')
note('Planner-aided and heuristic replays are labeled separately in the native viewer. No material grants, debug construction or future schedule are used. Native/headless agreement validates replay determinism for the tested recordings, not perfect fidelity to the commercial game.')

page('9 / What to do next','Use the measured checkpoint and preserve the comparison, rather than blindly extending an unchanged run.')
p(assessment['recommendation'])
heading('Run and view')
p('Open PowerShell in C:\\Users\\moham\\mini_motorways. The documented commands in training/QUICKSTART.md use the separate goal trainer for planner-aided experiments and the existing start_training.ps1 for the primitive policy. Every new run needs a fresh output folder. Ctrl+C saves and stops; a stop-file also supports graceful completion.')
p('To inspect the best recording: <font face="Arial-Bold">.venv/Scripts/python.exe training/watch_best.py --run output/training/'+assessment['best_run']+'</font>. Add --play to begin paused at the start instead of loading the final map.')
heading('Durable evidence and boundaries')
p('The archive contains run configs, source snapshots, summaries, progress/episode logs, frozen evaluations, exact best recordings, selection protocol and SHA-256 manifest. Model weights and generated game binaries remain local. GitHub contains the code, small evidence and PDF on mohammad; main remains the playground.')
p('Relevant checks covered simulator invariants, structured observation boundaries, input migration, actual gradient changes, checkpoint reloads, parallel workers, reward cancellation, no-op masks, shutdown and cross-runtime ordinary-command replays. The rebuilt native player passed the simulator check suite. Full test outcomes and any command corrections are recorded in the experiment log.')
heading('Open limits')
p('The experiments are small and adaptive. Development maps influenced engineering decisions, so they are not final tests. The planner uses approximate costs, can encounter ordinary rejection rules and redraws reused path segments. In five frozen initial development games, 438 of 668 accepted draw commands changed no network state; avoiding those is a future executor optimization, not a skill the current policy can learn inside a macro. The goal agent has fewer tools than the original policy. City transfer, replicated learning gains and the 1,000-trip target remain separate questions.')
note('Rebuild: docs/training/build_investigation_report.py using bundled Python with Matplotlib, ReportLab, Pillow and pypdf. The builder reads only archived files and never trains or runs a game. Historical PDFs are preserved. Primary shaping reference: Ng, Harada & Russell (1999), Policy Invariance Under Reward Transformations, ai.stanford.edu/~ang/papers/shaping-icml99.pdf.')

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#CFDDE2'));canvas.line(54,44,541,44)
    canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor(GREY))
    canvas.drawString(54,31,'Traffic Lab / completed investigation / 28 October 2026');canvas.drawRightString(541,31,str(doc.page))
SimpleDocTemplate(str(OUT),pagesize=(595,842),leftMargin=54,rightMargin=54,topMargin=45,bottomMargin=58,
                  title='Three-hour model investigation',author='Traffic Lab').build(story,onFirstPage=footer,onLaterPages=footer)
tracked=BASE/'model-investigation-2026-10-28.pdf';shutil.copyfile(OUT,tracked)
text='\n\n'.join(p.extract_text() for p in PdfReader(OUT).pages)
(DATA/'report-text.txt').write_text(text,encoding='utf-8')
artifacts=[tracked,Path(__file__),DATA/'assessment.json',DATA/'report-text.txt']+sorted(FIG.glob('*.png'))
artifacts.extend([DATA/'manifest.json',DATA/'README.md'])
if capture.exists():artifacts.append(capture)
(DATA/'report-manifest.json').write_text(json.dumps([dict(path=f.relative_to(BASE).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in artifacts],indent=2)+'\n')
print(OUT);print(f'{len(PdfReader(OUT).pages)} pages')
