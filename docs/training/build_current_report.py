"""Build the current model PDF from archived evidence, without running a policy."""
from pathlib import Path
import json
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
DATA=BASE/'evidence-2026-10-28'
WORK=ROOT/'tmp/pdfs/current-model-report'
WORK.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/pdf/mini_motorways_current_model_report.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
S=json.loads((DATA/'runs/seed-1000-parallel-02/summary.json').read_text())
INK='#183342';TEAL='#087F83';GOLD='#B55C17';GREY='#586F7D'
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyCustom',fontName='Arial',fontSize=10.2,leading=15,textColor=colors.HexColor(INK),spaceAfter=10))
styles.add(ParagraphStyle(name='TitleCustom',fontName='Arial-Bold',fontSize=28,leading=32,textColor=colors.HexColor(INK),spaceAfter=18))
styles.add(ParagraphStyle(name='HeadingCustom',fontName='Arial-Bold',fontSize=14,leading=19,textColor=colors.HexColor(TEAL),spaceBefore=12,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Arial',fontSize=8.2,leading=11.5,textColor=colors.HexColor(GREY),spaceAfter=8))
styles.add(ParagraphStyle(name='CellCustom',fontName='Arial',fontSize=9,leading=12,textColor=colors.HexColor(INK)))
W=487
story=[]
def p(text,style='BodyCustom'):story.append(Paragraph(text,styles[style]))
def heading(text):p(text,'HeadingCustom')
def page(title,sub=None):
    if story:story.append(PageBreak())
    p(title,'TitleCustom')
    if sub:p(sub)
def table(headers,rows,widths=None):
    data=[[Paragraph(str(v),styles['CellCustom']) for v in row] for row in [headers]+rows]
    t=Table(data,colWidths=widths or [W/len(headers)]*len(headers),hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEEEF')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor(TEAL)),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F6')])]))
    story.append(t);story.append(Spacer(1,10))
def figure(path,width=W):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:h=width*im.height/im.width
    story.append(Image(str(path),width=width,height=h));story.append(Spacer(1,8))
def note(text):p(text,'SmallCustom')

# New plots use only recorded evidence, not new simulator interaction.
fig,ax=plt.subplots(figsize=(8.3,3.5),layout='constrained')
x=range(3); groups=[('Starting sampled','before',-.24,'#7E909B'),('Final sampled','after',0,TEAL),('Final deterministic','deterministic_after',.24,GOLD)]
for label,key,offset,color in groups:
    vals=[r['trips'] for r in S[key]]
    ax.bar([v+offset for v in x],vals,width=.22,label=label,color=color)
    for v,n in zip(x,vals):ax.text(v+offset,n+.06,str(n),ha='center',fontsize=8)
ax.set(xticks=list(x),xticklabels=['2000','2001','2002'],xlabel='Held-out seed',ylabel='Completed trips',ylim=(0,4.5),title='Little transfer beyond the practiced layout')
ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,fontsize=8)
fig.savefig(WORK/'held-out.png',dpi=180);plt.close(fig)
trials=json.loads((DATA/'parallel-benchmark.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(8.3,3.2),layout='constrained')
for ax,key,title in [(axes[0],'selections_per_second','Policy selections / second'),(axes[1],'commands_per_second','Completed commands / second')]:
    means=[sum(t[key] for t in trials if t['workers']==n)/2 for n in [1,2,4]]
    ax.bar(['1 worker','2 workers','4 workers'],means,color=TEAL,width=.6)
    for i,v in enumerate(means):ax.text(i,v+1,f'{v:.1f}',ha='center',fontsize=8)
    ax.set(title=title,ylim=(0,max(means)*1.2));ax.spines[['top','right']].set_visible(False)
fig.savefig(WORK/'parallel-speed.png',dpi=180);plt.close(fig)

page('The current Mini Motorways model','Prepared for Mohammad | 28 October 2026 | Branch mohammad')
p('It learned greater consistency on one seed, then plateaued.','HeadingCustom')
p('This report explains the current learner and the latest completed experiment. The objective remains 1,000 completed trips on Los Angeles in OriginalReference. That goal has not been met.')
table(['Latest four-hour run','Measured outcome'],[
    ['Best observed game','73 trips; 461.4 simulated seconds'],
    ['Completed games',f"{S['episodes']:,}"],['Policy selections',f"{S['policy_steps']:,}"],
    ['Mean score: first / last 100 games','24.88 / 52.10'],['Held-out final sampled scores','3, 0, 0 on seeds 2000-2002'],
    ['Training device','CPU; four independent games, one shared model']],[210,W-210])
heading('How to read this report')
p('Pages 2-5 explain what it sees, what it can do, and how learning works. Pages 6-9 show results, transfer, the original baseline and throughput. Pages 10-12 cover fixes, decisions, unresolved limits and the exact input schema.')
note('Source: archived seed-1000-parallel-02 summary/config/monitor files. This was a resumed run, not training from random weights. OriginalReference is a reconstruction, not a validated exact copy of the commercial game. No additional training was performed to produce this report.')

page('1 / What the model can see','It reads structured numerical state, not the rendered game image.')
table(['Information','What enters the policy'],[
    ['Map and roads','Playable area, terrain, infrastructure categories, eight connection directions and pending demolition'],
    ['Buildings','Locations/footprints, kinds, colors, entrances, demand, reservations and overcrowding timers'],
    ['Traffic','Per-tile car count, maximum speed and maximum current waiting time'],
    ['Motorways','Endpoints, other-end coordinates, link number and retirement status'],
    ['Global state','Materials, time, week, trips, current upgrade offers and action-selection stage']],[115,W-115])
heading('The important missing information')
p('It does not receive each individual car\'s color, destination or route. It is not explicitly told which houses have a working connection to a matching destination. It must infer that relationship from the map.')
p('The policy has no recurrent memory and receives no stack of previous observations. Current waiting and overcrowding timers provide some accumulated state, but they are not a memory of past decisions.')
p('Future spawns, planned building changes and random-generator state are withheld. Cells outside playable bounds are zeroed. Values are normalized and clipped; multiple entities sharing a tile lose detail. London-specific rail/train channels are absent.')
note('Exact representation: 50 channels over 50 x 30 cells plus 42 global values. Current internal diagnostics are exposed; this is not claimed to be identical to a human player\'s visual information. Source: training/environment.py and its documented allowlist.')

page('2 / Actions and the network','All ordinary tools remain available, subject to current resources and targets.')
table(['Action','Selection after choosing a tool'],[
    ['Wait / upgrade','None; command completes immediately'],['Road, bridge, light, roundabout, remove','One tile'],
    ['Road stroke / house driveway','Start and end/direction tiles'],['Create motorway','Two endpoints'],
    ['Edit motorway','Existing endpoint plus two replacements'],['Remove motorway','An active endpoint']],[220,W-220])
p('The action vocabulary contains 1,513 IDs: 1,500 cells and 13 tools/upgrade choices. A command uses one to four policy selections. Intermediate selections advance no game time; a completed command advances 20 ticks, normally one simulated second. Rejected commands consume time too.')
heading('A compact actor-critic network')
table(['Stage','Shape / role'],[
    ['Map encoder','50 x 30 x 50 input; 16 then 24 convolution filters, 3 x 3 kernels, stride 2'],
    ['Combine','Flatten 2,496 features + 42 globals; project to 128 shared features'],
    ['Actor','64 hidden units; 1,513 action scores, filtered by the mask'],
    ['Critic','64 hidden units; one estimate of discounted future trip reward']],[110,W-110])
note('450,610 trainable parameters are numerical weights adjusted by optimization, not 450,610 rules or games. Masks remove locally unavailable choices; the host still decides final legality, including partial strokes. No path planner supplies routes. Sources: train.py, environment.py and original checkpoint inspection.')

page('3 / How it learns','Maskable PPO = Proximal Policy Optimization with unavailable actions masked out.')
table(['Step','What happens'],[
    ['Observe','Encode the current city and available choices.'],['Choose','Sample an allowed action from the actor\'s probabilities.'],
    ['Collect','Record observations, actions, rewards and critic predictions.'],['Estimate','Compare outcomes with predictions to estimate advantage.'],
    ['Update','Adjust weights using PPO\'s clipped policy objective, value loss and entropy term.'],['Repeat','Use the updated shared policy for new interactions.']],[90,W-90])
heading('The reward has only one component')
p('<b>reward = trips after the command - trips before the command</b>')
p('No completed trip means zero reward, even for a useful road. Two completed trips mean +2. There is no construction penalty, demolition penalty, survival bonus or explicit negative failure reward. Failure matters indirectly because it ends future opportunities for trips.')
p('Cars take time to deliver, so useful early decisions may receive credit much later. PPO and the critic estimate this connection; they do not automatically know what makes a correct road network. Intermediate endpoint choices also affect the selection-level discount.')
heading('Exploration versus deterministic playback')
p('Training samples actions to explore. Deterministic evaluation chooses the highest-probability allowed action. Watching the best recorded game replays exact commands; it does not ask the final model to recreate that game.')
note('PPO is on-policy: updates use recent rollouts, not a persistent replay dataset. A parameter update or low value loss alone does not establish better gameplay. The original report contains the schematic clipped probability-ratio objective and detailed glossary.')

page('4 / Current training configuration','Parallel games collect experience for one policy, not four independently trained models.')
table(['Setting','Current experiment'],[
    ['Version / city / materials','OriginalReference / Los Angeles / normal finite stock'],['Training seed','1000 only, repeatedly reset after game failure'],
    ['Held-out seeds','2000, 2001, 2002; excluded from training'],['Workers / device','4 simulator hosts / CPU; two PyTorch threads'],
    ['Aggregate rollout','256 selections = 64 per worker'],['Minibatch / epochs','64 / 4'],['Learning rate / optimizer','0.0003 / Adam'],
    ['Gamma / GAE lambda','0.999 / 0.95'],['PPO clip / entropy coefficient','0.2 / 0.01'],['Value coefficient / gradient norm cap','0.5 / 0.5'],
    ['Game cap','3,600 simulated seconds; ordinary failure usually occurs first'],['Latest learner budget','240 minutes or 10,000,000 selections, whichever first']],[210,W-210])
p('The run stopped normally at its four-hour learner limit. Setup, initial evaluation and final evaluation are outside that timer. Resuming keeps policy/optimizer weights but starts new episodes, metrics and a fresh timestep counter; it is not a saved live city.')
note('A label such as try 9/100 counts the current scheduling block. With one seed, reaching 100 starts another block on seed 1000; it does not stop training. Gamma discounts every policy selection, including intermediate selections. Shorter fragments with more workers may affect delayed credit. Sources: run config, train.py and parallel.py.')

page('5 / Four hours: what improved?','The model improved its usual score on the practiced layout, without setting a new best.')
figure(BASE/'four-hour-performance.png')
table(['Comparison','First 100 games','Last 100 games'],[['Mean score','24.88','52.10'],['Games scoring 50 or more','7 / 100','75 / 100']],[210,138,139])
p('Hourly mean scores were 31.97, 45.92, 52.64 and 52.64. The final two hours show a plateau in these averages. The best game still scored 73, matching the earlier record.')
table(['Total / rate','Measured result'],[['Learner wall time','14,400.7 seconds'],['Gameplay commands','1,650,223'],['Selections / second','157.7'],['Commands / second','114.6'],['Weight updates','Confirmed; final checkpoint saved']],[210,W-210])
note('Data: archived worker monitor CSV and summary.json, 4,549 completed games. Games are merged by monitor completion time. The rolling mean covers 100 games. Hour bins use monitor time and may exclude boundary completions; setup precedes the learner timer. First/last comparisons are within this resumed run, not random initialization versus final policy.')

page('6 / Did it learn other layouts?','The held-out evidence remains weak despite better training-seed consistency.')
figure(WORK/'held-out.png')
table(['Seed','Starting sampled','Final sampled','Final deterministic'],[
    [r['scenario_seed'],r['trips'],a['trips'],d['trips']] for r,a,d in zip(S['before'],S['after'],S['deterministic_after'])],[65,140,140,142])
p('On the practiced seed, the model learned a limited, repeatable pattern. On these unfamiliar seeds, final scores are only 0-3. This does not demonstrate a strong network-building strategy that transfers to other layouts.')
p('Three held-out seeds are a small evaluation, not a reliable estimate across all city variations. A broader, predeclared test would be required for a general performance claim. No transfer to the commercial game has been tested.')
note('Source: archived four-hour summary.json. Sampled and deterministic evaluations are different action-selection modes. The three evaluations are not independent training runs or a controlled comparison of learning algorithms.')

page('7 / How this compares with the beginning','Historical baseline: the first run, not the current policy.')
figure(BASE/'first-report-figures/scores.png')
p('The first run completed 242 games in 431.1 seconds. Only four games earned any trips; the best was seven. All held-out evaluations scored zero. The final deterministic replay spent 25 road tiles, then waited 116 times and failed with no trips.')
p('The later single-seed experiment clearly found more reliable ways to earn some trips. However, these runs differ in starting weights, seed schedule, duration and worker count. They do not isolate which change caused the improvement.')
note('Baseline: first-full-tools, revision 30ef7ab, 65,536 selections, 35,610 commands, random seeds 1000-1099. Baseline mean score 0.0413; all 242 games failed normally. The original 16-page report is preserved unchanged, including survival, optimizer, material-use and network/parameter graphics.')

page('8 / Can parallel games make it faster?','Yes for measured collection throughput; faster convergence is not established.')
figure(WORK/'parallel-speed.png')
p('Two short trials at each worker count measured about 60.3, 70.3 and 74.9 commands/second with one, two and four workers. That is roughly 17% and 24% more commands with two and four workers than one in this benchmark.')
p('These were 12-second trials after warm-up, in order 1/2/4/4/2/1, while another training run was active. They are under-load comparisons, not hardware maximums. Disposable clones performed brief learner updates without overwriting production weights.')
p('The completed four-hour run averaged 114.6 commands/second under its own workload. That number is not directly comparable to the short under-load benchmark. Games/second also depends on how long the model survives: better play can make each game take longer.')
heading('Why speed does not scale fourfold')
p('Simulator work runs in independent .NET processes, but Python JSON processing still shares the GIL. Policy calls are batched centrally. The thread-pool wrapper keeps large observation arrays in shared Python memory, avoiding another process-pipe copy.')
note('Sources: archived parallel-benchmark.json, parallel.py and latest summary. No deliberate 0.8-games/second limit was configured. Throughput is not a prediction of time to 1,000 trips.')

page('9 / Fixes since the first report','The learner, the viewer and the simulator need separate evidence.')
heading('Visible best-game recording')
p('Training now saves exact ordinary commands for the best game globally and per seed. Ranking is highest trips, then longest survival, then fewer rejected actions. Partial games can qualify at stop. The native viewer supports play, step, 1x/4x/16x, restart and reload-best.')
heading('Cars appearing to drive across grass')
p('Driveway edits removed the old connection from the drawn map immediately, while active cars retained committed lane snapshots and return routes. The viewer now draws pale gray retiring pavement until those trips clear. This does not reopen routing, alter stock or change the reward.')
heading('Ctrl+C crash during parallel training')
p('The earlier shutdown waited on failed workers before saving, and invalid pipes caused another error. Windows hosts now have separate process groups; interruption saves final.zip atomically before worker cleanup. Worker/replay cleanup failures produce warnings after the checkpoint is safe.')
p('The crashed run had no final.zip. Its valid latest.zip at 423,892 selections was used for the four-hour run. A periodic save can lose roughly the last two minutes before a crash. A new run folder is required when resuming.')
heading('What the checks establish')
p('Forty simulator suites, seven environment tests, four workflow tests, three parallel tests, the shutdown test and five-map protocol checks passed at the fix revision. The earlier 73-trip/479.8-second/480-command replay verified in headless and native runtimes. That is a different recording from the latest 73-trip/461.4-second best.')
note('Source: revision e6119eb and documented validation. Exact command replay and internal tests do not establish commercial-game parity. Roundabout connectors, parking and other rendering/geometry approximations remain documented limits.')

page('10 / Decisions and what comes next','Preserve the task while testing specific explanations for the plateau.')
table(['Decision / change','Status'],[
    ['High score, OriginalReference, structured input, trial and error, all tools','User-selected task; 1,000 trips remains provisional goal'],
    ['Branch mohammad; main stays playground','Implemented and published to GitHub'],['Repeated seed practice, then one seed only','Implemented; faster learning was a hypothesis, not a controlled result'],
    ['Best-game maps and live seed/wait/ETA output','Implemented'],['Parallel collection and four-hour run','Implemented and explicitly authorized; run completed'],
    ['Every update, decision, analysis and performance finding documented','Ongoing project requirement; report/graphs/evidence archived']],[245,W-245])
heading('Recommended next investigation, not implemented')
p('Inspect recurring failure states and count working house-to-destination connections, material waste and missed demand. Then compare one targeted change at a time. Candidate bottlenecks include spatial action coordination, missing connectivity features, delayed credit, sparse reward and exploration.')
p('No connectivity labels, new reward shaping, route suggestions, demonstrations or recurrent memory have been added. The observations suggest possible bottlenecks; they do not prove a single cause. More unchanged four-hour training is not currently recommended.')
note('The original report\'s proposals are still proposals unless the history explicitly records their implementation. No new training was started for this report. User choices, engineering choices, measured facts and hypotheses are separated in training/EXPERIMENT_HISTORY.md.')

page('11 / Exact inputs and evidence','Reference for checking what changed between model versions.')
table(['Grid channel','Encoding'],[
    ['0','Playable-cell visibility'],['1-3 / 4-8 / 9-11','Terrain / infrastructure / building-kind categories'],['12-19 / 20-27','Building colors / eight connection bits'],
    ['28','Pending removal'],['29-31','Demand / 20; reservations / 20; overcrowding / 50'],['32-39','Eight entrance/driveway directions'],
    ['40-42','Car count / 10; max speed / 2; max current wait / 60'],['43-47','Motorway endpoint; retirement; other x / 50, y / 30; number / 20'],
    ['48-49','First selected cell; existing selected motorway endpoint']],[100,W-100])
table(['Global indices','Encoding'],[['0-5','Six inventories: roads / 100, other materials / 10'],['6-8','Time / cap; week / 100; trips / 1000'],['9-24','Two offers: six type flags, amount / 100, roads / 100 each'],['25-28 / 29-41','Four action phases / thirteen selected tools']],[100,W-100])
note('All inputs clip to [0, 1]. Schema: full-tools-staged-grid-v1. Unknown colors, changed grid sizes or more than two upgrade offers raise errors rather than being silently truncated.')
heading('Evidence and reproduction')
note('Latest run: seed-1000-parallel-02; source e6119eb; resumed parallel-01/latest.zip; 240-minute budget. Sources: archived configs, summaries, episodes, monitor and optimizer CSV under docs/training/evidence-2026-10-28/. The evidence index includes hash manifests and all historical PDF figures. Checkpoints/player binaries remain local and are not backed up by the documentation archive.')
note('Readable sources: training/README.md (contract), CURRENT_STATUS.md (latest results), EXPERIMENT_HISTORY.md (decisions/analysis), QUICKSTART.md (commands), docs/training/README.md (evidence). Rebuild source: docs/training/build_current_report.py. Algorithm explanations follow the implemented SB3-Contrib MaskablePPO setup and the original report\'s PPO references; no algorithm comparison was performed.')

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor('#D4E1E5'));canvas.line(54,48,541,48)
    canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor(GREY))
    canvas.drawString(54,34,'MOHAMMAD / CURRENT MODEL / 28 OCTOBER 2026')
    canvas.drawRightString(541,34,f'{doc.page:02d}');canvas.restoreState()
doc=SimpleDocTemplate(str(OUT),pagesize=(595.28,841.89),leftMargin=54,rightMargin=54,topMargin=48,bottomMargin=64,
    title='Mini Motorways - Current Model Report - 28 October 2026',author='Mohammad / Codex')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
shutil.copy2(OUT,BASE/'current-model-report-2026-10-28.pdf')
from pypdf import PdfReader
text=['# Current model report: searchable text\n\nExtracted from the dated 12-page PDF; use the PDF for graphs and layout.\n']
for i,part in enumerate(PdfReader(OUT).pages,1):
    text.append(f'\n## PDF page {i}\n\n'+part.extract_text()+'\n')
(BASE/'CURRENT_REPORT_TEXT.md').write_text('\n'.join(text).rstrip()+'\n',encoding='utf-8')
for name in ['held-out.png','parallel-speed.png']:shutil.copy2(WORK/name,BASE/('current-'+name))
print(OUT)
