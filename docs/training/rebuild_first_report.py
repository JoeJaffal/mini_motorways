from pathlib import Path
import csv, json, math
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'tmp/pdfs/archived-model-report'
WORK.mkdir(parents=True,exist_ok=True)
RUN=ROOT/'docs/training/evidence-2026-10-28/runs/first-full-tools'
OUT=ROOT/'output/pdf/first-model-report-rebuilt.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
S=json.loads((RUN/'summary.json').read_text())
C=json.loads((RUN/'config.json').read_text())
E=[json.loads(x) for x in (RUN/'episodes.jsonl').read_text().splitlines()]
R=json.loads((ROOT/'docs/training/evidence-2026-10-28/first-report-replay.json').read_text())
with (RUN/'progress.csv').open() as f: P=list(csv.DictReader(f))
def col(k): return np.array([float(x[k]) if x[k] else np.nan for x in P])
scores=np.array([x['trips'] for x in E]); survival=np.array([x['seconds'] for x in E]); episodes=np.arange(1,len(E)+1)
INK='#172B3A'; TEAL='#007F82'; GOLD='#D09522'; RED='#B94444'; GREY='#637785'; LIGHT='#EDF3F5'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':11,'axes.labelsize':9,
 'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#BCCBD1','text.color':INK,
 'axes.labelcolor':INK,'xtick.color':GREY,'ytick.color':GREY,'grid.color':'#E4ECEF','figure.facecolor':'white',
 'axes.titleweight':'bold','savefig.facecolor':'white'})
def save(fig,name):
    fig.savefig(WORK/(name+'.png'),dpi=230,bbox_inches='tight',pad_inches=.14)
    plt.close(fig)
def chart_scores():
    fig,ax=plt.subplots(2,1,figsize=(8.5,5.2),layout='constrained',gridspec_kw={'height_ratios':[1.8,1]})
    ax[0].scatter(episodes,scores,color=TEAL,s=15,zorder=3)
    ax[0].plot(episodes,scores,color=TEAL,alpha=.25,lw=.8)
    ax[0].set(xlabel='Completed training episode',ylabel='Trips completed',ylim=(-.35,8.3),title='Only four training games completed any trips')
    n=int(np.argmax(scores))
    ax[0].annotate('7 trips',(n+1,scores[n]),xytext=(6,8),textcoords='offset points',fontsize=8)
    ax[0].annotate('Three games with 1 trip each',(19,1),xytext=(58,2.5),
                   arrowprops={'arrowstyle':'-','color':GREY,'linewidth':.8},fontsize=8)
    ax[0].grid(axis='y',alpha=.7)
    means=np.convolve(scores,np.ones(20)/20,mode='valid')
    ax[1].plot(np.arange(20,len(E)+1),means,color=GOLD,lw=2)
    ax[1].set(xlabel='Episode at end of 20-game window',ylabel='Mean trips',ylim=(-.02,.62),title='20-game rolling mean returns to zero')
    ax[1].grid(axis='y',alpha=.7)
    save(fig,'scores')
def chart_survival():
    fig,ax=plt.subplots(1,2,figsize=(8.5,3.4),layout='constrained',gridspec_kw={'width_ratios':[1.8,1]})
    ax[0].scatter(episodes,survival,c=np.where(scores>0,GOLD,TEAL),s=12,alpha=.8)
    ax[0].set(xlabel='Completed training episode',ylabel='Simulated seconds',title='Survival stays short',ylim=(120,225))
    ax[0].grid(axis='y',alpha=.7)
    ax[1].bar(['Zero trips','Positive trips'],[238,4],color=[GREY,GOLD],width=.55)
    for i,v in enumerate([238,4]): ax[1].text(i,v+5,str(v),ha='center',fontweight='bold')
    ax[1].set(ylabel='Completed episodes',ylim=(0,265),title='Reward is very sparse')
    save(fig,'survival')
def chart_diagnostics():
    fig,ax=plt.subplots(2,2,figsize=(8.5,5.1),layout='constrained')
    x=col('time/total_timesteps')/1000
    for a,k,title,color in [(ax[0,0],'train/entropy_loss','Masked action entropy (negative loss)',TEAL),
      (ax[0,1],'train/approx_kl','Approximate KL divergence',GOLD),
      (ax[1,0],'train/clip_fraction','Fraction of ratios outside PPO clip range',GREY),
      (ax[1,1],'train/value_loss','Value prediction loss (log scale)',RED)]:
        v=col(k); v=-v if 'entropy' in k else v
        a.plot(x,v,color=color,lw=1)
        a.set(title=title,xlabel='Policy decisions (thousands)')
        a.grid(axis='y',alpha=.5)
    ax[1,1].set_yscale('log')
    save(fig,'diagnostics')
def chart_speed():
    fig,ax=plt.subplots(1,2,figsize=(8.5,2.9),layout='constrained')
    x=col('time/total_timesteps')/1000
    ax[0].plot(x,col('time/fps'),color=TEAL,lw=1.7)
    ax[0].set(title='Cumulative learner throughput',xlabel='Policy decisions (thousands)',ylabel='Policy decisions / second',ylim=(0,180))
    ax[1].plot(col('time/time_elapsed')/60,x,color=TEAL,lw=1.7)
    ax[1].set(title='Completed interaction budget',xlabel='Logged learner wall time (minutes)',ylabel='Policy decisions (thousands)')
    for a in ax:a.grid(axis='y',alpha=.7)
    save(fig,'speed')
def draw_map(ax,o,title):
    vis=np.zeros((30,50),bool)
    for y in range(30):
        for x in range(50):vis[y,x]=o['playableXMin']<=x<o['playableXMax'] and o['playableYMin']<=y<o['playableYMax']
    a=np.array(o['terrain']).reshape(30,50)
    rgb=np.ones((30,50,3))
    from matplotlib.colors import to_rgb
    for n,color in [(0,'#F0F4EB'),(1,'#B9DFE9'),(2,'#CFD2D4')]:rgb[a==n]=to_rgb(color)
    rgb[~vis]=to_rgb('#F1F3F5')
    ax.imshow(rgb,extent=(-.5,49.5,29.5,-.5),interpolation='nearest')
    road=np.array(o['infrastructure']).reshape(30,50)
    y,x=np.where((road>0)&vis)
    ax.scatter(x,y,s=22,marker='s',color=INK,zorder=4)
    dirs=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
    for k,bits in enumerate(o['connections']):
        p=(k%50,k//50)
        if not vis[p[1],p[0]]:continue
        for d,(dx,dy) in enumerate(dirs):
            q=(p[0]+dx,p[1]+dy)
            if bits&(1<<d) and 0<=q[0]<50 and 0<=q[1]<30 and vis[q[1],q[0]]:
                ax.plot([p[0],q[0]],[p[1],q[1]],color=TEAL,lw=1.3,zorder=3)
    palette=['#E7A536','#D35460','#4A96BC','#86AE75','#8C77B5','#D280B4','#AD9453','#68B5B5']
    for b in o['buildings']:
        x,y=b['cell']['x'],b['cell']['y']
        if not vis[y,x]:continue
        ax.add_patch(Rectangle((x-.4,y-.4),b['width']-.2,b['height']-.2,facecolor=palette[b['color']],edgecolor='white',lw=1,zorder=5))
        ax.text(x+(b['width']-1)/2,y+(b['height']-1)/2,'H' if b['isHouse'] else 'D',ha='center',va='center',fontsize=6.5,color=INK,zorder=6,fontweight='bold')
    ax.set(xlim=(o['playableXMin']-1,o['playableXMax']),ylim=(o['playableYMax'],o['playableYMin']-1),title=title,xlabel='Grid x',ylabel='Grid y')
    ax.set_aspect('equal');ax.tick_params(labelsize=7)
def chart_maps():
    fig,ax=plt.subplots(1,2,figsize=(8.5,3.5),layout='constrained')
    draw_map(ax[0],R['snapshots'][0]['observation'],'Reset: no player road tiles')
    draw_map(ax[1],R['snapshots'][1]['observation'],'After 25 commands: stock exhausted')
    save(fig,'maps')
    fig,ax=plt.subplots(1,2,figsize=(8.5,2.55),layout='constrained',gridspec_kw={'width_ratios':[1.9,1]})
    t=[0]+[x['seconds'] for x in R['trace']];stock=[25]+[x['roads'] for x in R['trace']]
    ax[0].step(t,stock,where='post',color=TEAL,lw=2)
    ax[0].set(xlabel='Simulated seconds',ylabel='Road tiles available',title='25 tiles used in the first 25 seconds',ylim=(-1,28))
    ax[0].grid(axis='y',alpha=.6)
    ax[1].barh(['Wait','Place road'],[116,25],color=[GREY,TEAL])
    for y,v in enumerate([116,25]):ax[1].text(v+2,y,str(v),va='center')
    ax[1].set(xlabel='Completed commands',xlim=(0,140),title='Actions in this replay')
    save(fig,'inventory')
def chart_eval():
    fig,ax=plt.subplots(figsize=(8.5,2.8),layout='constrained')
    labels=['Initial\nsampled','Final\nsampled','Final\nhighest probability']
    for i in range(3):
        ax.scatter(np.array([-.13,0,.13])+i,[0,0,0],s=65,c=[TEAL,GOLD,RED],edgecolor='white',zorder=4)
        ax.text(i,.12,'0, 0, 0',ha='center',fontsize=11,fontweight='bold')
    ax.set(xticks=range(3),xticklabels=labels,ylabel='Trips per held-out game',ylim=(-.15,1),title='All nine evaluation games scored zero')
    ax.grid(axis='y',alpha=.7)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=c,label=f'Seed {s}',markersize=7) for s,c in zip([2000,2001,2002],[TEAL,GOLD,RED])],loc='upper right',frameon=False,ncol=3)
    save(fig,'evaluation')
def chart_params():
    fig,ax=plt.subplots(figsize=(8.5,2.6),layout='constrained')
    labels=['Feature projection','Action head','Actor + critic hidden','Convolutions','Value head']
    values=[324992,98345,16512,10696,65]
    ax.barh(labels,values,color=[TEAL,GOLD,GREY,GREY,GREY])
    for i,v in enumerate(values):ax.text(v+4500,i,f'{v:,}',va='center',fontsize=8)
    ax.set(xlabel='Trainable parameters',xlim=(0,385000));ax.invert_yaxis();ax.ticklabel_format(axis='x',style='plain')
    save(fig,'parameters')
for fn in [chart_scores,chart_survival,chart_diagnostics,chart_speed,chart_maps,chart_eval,chart_params]:fn()

pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic','C:/Windows/Fonts/ariali.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Arial',fontSize=10.2,leading=14.6,textColor=colors.HexColor(INK),spaceAfter=9))
styles.add(ParagraphStyle(name='SmallText',parent=styles['Body'],fontSize=8.4,leading=11.7,spaceAfter=6,textColor=colors.HexColor(GREY)))
styles.add(ParagraphStyle(name='TitleX',fontName='Arial-Bold',fontSize=25,leading=29,textColor=colors.HexColor(INK),spaceAfter=13))
styles.add(ParagraphStyle(name='SubX',fontName='Arial-Bold',fontSize=12.5,leading=17,textColor=colors.HexColor(TEAL),spaceBefore=8,spaceAfter=8))
styles.add(ParagraphStyle(name='Eyebrow',fontName='Arial-Bold',fontSize=9,leading=13,textColor=colors.HexColor(TEAL),spaceAfter=8))
styles.add(ParagraphStyle(name='CellX',fontName='Arial',fontSize=9,leading=12,textColor=colors.HexColor(INK)))
styles.add(ParagraphStyle(name='CodeX',fontName='Courier',fontSize=8.3,leading=12,textColor=colors.HexColor(INK),spaceAfter=10))
story=[]; W=487.28
def p(text,kind='Body'):story.append(Paragraph(text,styles[kind]))
def sub(text):p(text,'SubX')
def gap(n=6):story.append(Spacer(1,n))
def page(n,title,lead):
    if n>1:story.append(PageBreak())
    p(f'MINI MOTORWAYS / MODEL REPORT / {n:02d}','Eyebrow');p(title,'TitleX');p(lead)
def table(headers,rows,widths=None):
    data=[[Paragraph(str(c),styles['CellX']) for c in row] for row in [headers]+rows]
    t=Table(data,colWidths=widths or [W/len(headers)]*len(headers),hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(LIGHT)),('VALIGN',(0,0),(-1,-1),'TOP'),
      ('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor(TEAL)),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DCE6E9')),
      ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t);gap(8)
def note(text):
    t=Table([[Paragraph(text,styles['Body'])]],colWidths=[W]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(LIGHT)),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#CBDEE1')),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.append(t);gap(9)
def fig(name,height=None,caption=''):
    from PIL import Image as PI
    path=WORK/(name+'.png');im=PI.open(path);h=W*im.height/im.width
    if height and h>height: w=W*height/h;h=height
    else:w=W
    story.append(Image(str(path),width=w,height=h,hAlign='CENTER'))
    if caption:p(caption,'SmallText')
    gap(5)
def diagram(rows):
    # Each row is a three-column data-flow drawing; labels are intentionally brief.
    height=len(rows)*67+6;d=Drawing(W,height)
    bw=(W-36)/3
    for row,items in enumerate(rows):
        y=height-58-row*67
        for j,(title,detail) in enumerate(items):
            x=j*(bw+18)
            d.add(Rect(x,y,bw,48,rx=6,ry=6,fillColor=colors.HexColor(LIGHT),strokeColor=colors.HexColor('#C7D9DE')))
            d.add(String(x+9,y+29,title,fontName='Arial-Bold',fontSize=9,fillColor=colors.HexColor(INK)))
            d.add(String(x+9,y+13,detail,fontName='Arial',fontSize=8,fillColor=colors.HexColor(GREY)))
            if j<2:
                d.add(Line(x+bw+3,y+24,x+bw+14,y+24,strokeColor=colors.HexColor(TEAL)))
                d.add(Polygon([x+bw+14,y+24,x+bw+10,y+27,x+bw+10,y+21],fillColor=colors.HexColor(TEAL),strokeColor=None))
    story.append(d);gap(4)
def network_fork():
    d=Drawing(W,90)
    d.add(String(W/2,78,'SHARED 128-VALUE CITY FEATURES',textAnchor='middle',fontName='Arial-Bold',fontSize=8.5,fillColor=colors.HexColor(TEAL)))
    for x,title,detail in [(0,'ACTOR: 64 HIDDEN','1,513 logits -> mask -> probabilities'),(257,'CRITIC: 64 HIDDEN','One expected future-return estimate')]:
        d.add(Rect(x,5,230,48,rx=6,ry=6,fillColor=colors.HexColor(LIGHT),strokeColor=colors.HexColor('#C7D9DE')))
        d.add(String(x+10,34,title,fontName='Arial-Bold',fontSize=9,fillColor=colors.HexColor(INK)))
        d.add(String(x+10,18,detail,fontName='Arial',fontSize=8,fillColor=colors.HexColor(GREY)))
        d.add(Line(W/2,72,x+115,55,strokeColor=colors.HexColor(TEAL)))
    story.append(d)

page(1,'Inside the first\nMini Motorways model'.replace('\n','<br/>'),
     'A visual explanation of the model, its learning process and the first local experiment. Prepared for Mohammad on 28 October 2026.')
note('<b>The pipeline works. The strategy does not yet.</b><br/>The model trained and its checkpoints reload, but all held-out evaluation scores remain zero. The 1,000-trip objective is still a research goal.')
table(['7 min 11 sec','242 games','7 trips'],[['Learner runtime','Completed training episodes','Best observed training score']], [W/3]*3)
sub('What this model is')
p('A small neural network that chooses construction commands in the <b>OriginalReference</b> simulator. It receives structured numerical game state and learns through trial and error using <b>Maskable PPO</b>. It has 450,610 trainable parameters and runs on the CPU.')
diagram([[('OBSERVE','Current city and materials'),('DECIDE','Tool, cells and upgrade'),('LEARN','Compare outcomes to estimates')]])
sub('Read the report')
table(['Topic','Pages'],[['Experiment and hardware','2'],['Inputs, tools and neural network','3-5'],['How reward and PPO work','6-7'],['Training, survival and optimizer graphs','8-10'],['Actual behavior and held-out evaluation','11-12'],['Interpretation, reproduction and reference','13-16']],[W-65,65])
p('All performance graphs come from the saved first run. Map panels are schematic reconstructions from simulator observations. Explanatory flow diagrams are conceptual. No additional training was performed to create this report.','SmallText')

page(2,'The experiment we actually ran','The setup follows the agreed goal: high trip score, OriginalReference, structured state, all tools and learning through trial and error.')
table(['Setting','Actual configuration'],[['City and version','Los Angeles / OriginalReference'],['Environment rules','Finite materials; ordinary spawning and overcrowding failure'],['Training distribution','Seeds 1000-1099; 91 distinct seeds observed in 242 completed games'],['Held-out seeds','2000, 2001, 2002; excluded from training'],['Decision budget','65,536 policy selections; 35,610 completed gameplay commands'],['Stop rule','Decision budget or 29.5 minutes of learner time, whichever comes first'],['Episode cap','3,600 simulated seconds; all completed games failed before the cap'],['Device','Intel i7-1185G7, 32 GB RAM; CPU PyTorch, two threads, one host']],[125,W-125])
fig('speed',205,'Source: progress.csv. Throughput includes simulator interaction and optimizer work; it is a cumulative rate, not an isolated inference benchmark.')
p('<b>Measured:</b> 152.0 policy decisions/s and 82.6 completed commands/s. The sampled Python working set was about 378 MB; that is not a system-wide peak measurement. Installation, tests and evaluation are outside the 431.1-second learner time.')

page(3,'What the model can see','The network receives numerical arrays, not screenshots. A grid encodes where things are; a small global vector describes resources and the current selection stage.')
diagram([[('50 x 30 CELLS','The simulator canvas'),('50 CHANNELS','Terrain, roads, demand...'),('42 GLOBAL VALUES','Stock, time, offers, phase')]])
table(['Visible current information','How it enters the network'],[['Terrain and construction','One-hot categories, eight connection bits and pending removals'],['Buildings','Kinds, colors, demand, reservations, entrance direction and overcrowding timer'],['Vehicles','Per-cell count, maximum speed and maximum current waiting'],['Motorways','Endpoints, retirement flag, other endpoint coordinates and number'],['Global state','Six inventories, time, week, score and two current upgrade offers'],['Selection state','Chosen tool, current phase and selected cell markers']],[145,W-145])
sub('Information deliberately withheld')
p('Scheduled future spawns, building upgrade times, planned demand multipliers, random-generator diagnostics and offer-generation weights are excluded. Cells outside the current playable bounds are zeroed.')
note('<b>This is a documented structured-state interface.</b> It exposes current internal quantities such as reservations and overcrowding timers. It does not claim to reproduce exactly what a human sees on screen.')
p('Values are normalized and clipped to [0, 1]. Variable lists are rasterized or aggregated rather than cut to a fixed list length. Some distinct entities can therefore share a cell and lose detail. The encoder is designed for Los Angeles; it does not include London-specific rail/train channels. Full channel indices appear on page 15.','SmallText')

page(4,'What the model can do','The model chooses both the construction tool and its target cells. A route planner does not suggest house-to-destination paths.')
table(['Action family','Selections after choosing the tool'],[['Wait / weekly upgrade 0 or 1','None; the command completes immediately'],['Road / bridge / light / roundabout / demolition','One target cell'],['Draw a road stroke','Start and end cells; the host may partially build the stroke'],['Change a house driveway','House cell and an adjacent direction cell'],['Create a motorway','Two endpoint cells'],['Edit a motorway','An existing endpoint, then two replacement endpoints'],['Remove a motorway','One of its active endpoints']],[190,W-190])
sub('A command is a bounded sequence')
diagram([[('1. CHOOSE TOOL','Example: draw a road'),('2. CHOOSE START','A grid-cell ID'),('3. CHOOSE END','Command then time step')]])
p('The vocabulary has <b>1,513 IDs</b>: 1,500 cells and 13 tools or upgrade choices. The meaning of a cell ID depends on the current phase. A motorway edit needs at most four selections; the phase sequence cannot loop forever.')
note('<b>Action masks filter obvious unavailable choices.</b> For example, no motorway creation without stock, no demolition of an empty cell, and no selection outside the playable area. The simulator still decides final legality; crossing conflicts and partial strokes can be rejected or only partly succeed.')
p('A completed or invalid command advances 20 simulation ticks, normally one simulated second. Intermediate selections advance no time and earn no reward. An impossible continuation completes a wait. Reset, step controls, stock grants and the debug reference-road command are not model choices.')

page(5,'Inside the neural network','This is a compact actor-critic network. The actor chooses actions; the critic estimates future reward from the current observation. Both use the same encoded city features.')
diagram([[('GRID: 50 x 30 x 50','Channels x height x width'),('CONVOLUTION 1','16 filters; 3 x 3; stride 2'),('CONVOLUTION 2','24 filters; 3 x 3; stride 2')],
 [('FLATTEN: 2,496','24 x 8 x 13 features'),('ADD 42 GLOBALS','2,538 input values'),('PROJECT TO 128','Linear layer + ReLU')]])
network_fork()
p('The actor and critic branch independently from the shared 128-value feature vector. ReLU is a nonlinear activation that lets layers learn more than a linear mapping.')
fig('parameters',180,'Source: final checkpoint parameter inspection. Total = 450,610 trainable parameters.')
p('Training samples from the masked probabilities to explore. Deterministic evaluation chooses the highest-probability allowed action. There is no language model, demonstration dataset, recurrent memory or human-written routing policy inside this network.')

page(6,'How a trip becomes a lesson','The model starts with randomly initialized weights. It tries actions, receives a reward and changes its action probabilities based on how the observed outcome compares with its prediction.')
diagram([[('COLLECT 256 SELECTIONS','State, action, reward, value'),('ESTIMATE ADVANTAGES','Was this better than expected?'),('UPDATE THE NETWORK','Four passes over the batch')]])
sub('The entire reward rule')
note('<b>reward = completed_trips_after - completed_trips_before</b><br/>The difference spans the gameplay command plus its subsequent simulation step. There is no construction cost penalty, survival bonus or explicit failure penalty in the reward.')
table(['Example transition','Reward'],[['Build a legal road; no trip finishes','0'],['Reject a road; time still advances; no trip finishes','0'],['Two trips finish during a completed transition','+2'],['Choose an intermediate endpoint; no command yet','0'],['City fails without another completed trip','0; episode ends']],[W-65,65])
sub('Credit arrives late')
p('A useful road can take several selections to construct. Cars then need time to drive before a trip is counted. The learner must associate later trips with earlier decisions. Discounted returns and the critic help estimate that connection; they do not identify a correct route automatically.')
p('Failure ends access to future trip rewards, so it can matter indirectly even without a negative terminal reward. But if almost all experiences contain zero trips, there is very little signal distinguishing one unsuccessful layout from another. This happened in the first run.')
p('PPO is an on-policy method: new updates use recently collected interactions from the current policy. It does not maintain a persistent experience-replay dataset like some other reinforcement-learning algorithms. [R6, R7]','SmallText')

page(7,'How PPO changes the weights','The critic estimates expected future trip reward. The actor is encouraged to favor actions with positive estimated advantage while PPO clipping limits incentives for overly large probability changes.')
p('<b>Advantage</b> means an action did better or worse than the critic expected. Estimates are noisy, especially when rewards are scarce. Generalized advantage estimation combines reward prediction errors over successive selections.','Body')
p('ratio = new_probability / old_probability<br/>policy_objective = mean(min(ratio * advantage,<br/>                         clip(ratio, 0.8, 1.2) * advantage))','CodeX')
p('This is the core clipped policy objective, shown schematically. The implementation also uses a value-prediction loss and an entropy term. An entropy bonus encourages a broader action distribution; it does not guarantee useful exploration. Clipping is not a hard guarantee on the size of every policy change. [R6, R7]')
table(['Parameter','Run value','Practical role'],[['Rollout length','256 selections','New interactions before an update'],['Minibatch / epochs','64 / 4','Four minibatches per pass, four passes per rollout'],['Learning rate','0.0003','Adam optimizer step scale'],['Discount gamma','0.999','How future selection-level reward is weighted'],['GAE lambda','0.95','Balances advantage-estimation trade-offs'],['PPO clip range','0.2','Clipped probability-ratio objective'],['Entropy / value weights','0.01 / 0.5','Exploration term and critic-loss weighting'],['Gradient norm cap','0.5','Limits gradient norm before optimizer steps']],[130,85,W-215])
p('<b>Important timing detail:</b> gamma applies per policy selection, including intermediate endpoint selections, not per simulated second. One command can involve one to four selections. Thus command types have different selection lengths.')
p('65,536 / 256 = 256 rollout batches. Four epochs each give 1,024 training epochs; four minibatches per epoch give 4,096 Adam steps. These counts were checked in the saved model. The last CSV row logs the previous update count (1,020), before the final four epochs complete.','SmallText')

page(8,'Did the scores improve?','No sustained improvement is visible. Positive outcomes occurred only in episodes 9, 17, 19 and 26; every later completed training episode scored zero.')
fig('scores',330,'Source: episodes.jsonl, 242 completed training episodes. The score axis is deliberately zoomed to the observed 0-7 range; the goal remains 1,000 trips.')
table(['Best episode','Mean episode score','Last 30 games'],[['7 trips at episode 9','10 total trips / 242 games = 0.0413','All scored 0']],[W/3]*3)
p('The best exploratory result is not the final policy\'s expected score. A single lucky network can yield trips without becoming a strategy that the model can reproduce. Training scores also come from training seeds; held-out performance is the stronger practical check.')

page(9,'How often did it find reward?','Only 4 of 242 completed games produced any trips: 1.65%. All 242 ended through normal game failure; none reached the external 3,600-second cap.')
fig('survival',245,'Source: episodes.jsonl. Gold points are games with at least one completed trip. These are observations from one training run, not independent algorithm comparisons.')
table(['Episode','Seed','Trips'],[['9','1020','7'],['17','1051','1'],['19','1083','1'],['26','1064','1']],[90,110,W-200])
p('The longest completed game lasted 210.05 simulated seconds. Because even the longest episode is far below the cap, increasing that cap alone would not have helped this run survive longer.')
note('<b>Interpretation, not proof of a single cause:</b> the rarity of reward supports an exploration/coordination diagnosis. The logs do not isolate whether the main cause is tool selection, spatial representation, delayed credit, optimization settings or their interaction.')

page(10,'The optimizer was active','These diagnostics show how the optimizer behaved. They should be read alongside score and evaluation results, not used as substitutes for game performance.')
fig('diagnostics',330,'Source: progress.csv. Entropy is plotted as the negative of the logged entropy loss. Gaps at the first row reflect metrics that were not yet available.')
table(['Graph','What it can and cannot tell us'],[['Masked action entropy','The action distribution becomes less diffuse overall. Masks and phase mix also change entropy, so this is not a clean measure of strategic exploration.'],['Approximate KL / clip fraction','Describe probability-distribution changes and use of the clipped objective. They do not measure correct road planning.'],['Value prediction loss','The critic fits its return targets. Very low loss is compatible with repeatedly predicting zero reward in zero-trip games.']],[125,W-125])
p('The final checkpoint has different weights from the starting checkpoint. That establishes parameter updates, not successful learning of a useful construction policy.','SmallText')

page(11,'Watch the saved model act','A fresh-process replay of the final checkpoint, seed 2000, using highest-probability actions. This is one recorded evaluation behavior, not a claim about every possible seed or stochastic action sequence.')
fig('maps',215,'Schematic simulator-state maps. H = house, D = destination; colors indicate destination groups. Dark squares are player road tiles, teal lines are actual road links. Terrain is pale land, blue water and gray blocked cells. Axes are grid coordinates.')
fig('inventory',170,'Source: replay of final.zip captured for this report. No weights were updated. Completed commands: 25 single road placements, then 116 waits.')
p('By command 25, all starting road tiles have been spent. This behavior never chooses the draw/connect stroke. Ordinary road placement may attach a designated driveway automatically, but neighboring ordinary roads are not generally linked merely because both tiles exist.')
note('<b>Observed outcome:</b> zero trips; normal game failure at 140.1 simulated seconds. The replay illustrates a concrete failure mode: spending material without constructing a productive connected route.')

page(12,'Test on seeds it never trained on','The same three held-out seeds were tested before learning and after loading the final checkpoint. Final evaluation used both sampled and highest-probability action selection.')
fig('evaluation',210,'Source: summary.json. Three colored points at each setting represent seeds 2000-2002. Zero values are labeled because zero-height bars would hide the result.')
table(['Seed','Initial sampled','Final sampled','Final highest-probability'],[['2000','0','0','0'],['2001','0','0','0'],['2002','0','0','0']],[65,130,130,W-325])
p('Every evaluation game ended through normal failure, at 139.55-140.75 simulated seconds. No evaluation reached the time cap. The final model therefore shows no held-out score improvement in this small test.')
sub('Why three seeds are a limited test')
p('Three seeds cannot establish robust generalization across all city variations. They are sufficient to reject a claim that this particular final checkpoint demonstrated reliable high scoring here. A later model would need a broader, predeclared evaluation before any strong performance claim.')
p('Sampled evaluation uses a fixed PyTorch seed for repeatability. The initial and final policy still produce different trajectories; using a common seed does not make the games statistically identical.','SmallText')

page(13,'What this tells us - and what to try','The PC can execute this experiment at a practical rate. The first model has not learned the intended game strategy. More compute is not, by itself, evidence that this exact setup will reach 1,000 trips.')
table(['Evidence','Reasonable conclusion'],[['152 decisions/s, 82.6 commands/s','The measured small CPU pipeline is feasible locally.'],['Reward in only 4 of 242 games','Useful construction outcomes are rare under current exploration.'],['7-trip best early; later scores zero','The run did not sustain or reproduce its best exploratory outcome.'],['Final replay spends roads, then waits','Tool and connection coordination need attention.'],['All held-out scores remain zero','The 1,000-trip success criterion is not met.']],[205,W-205])
sub('Proposed next experiments - not performed')
p('<b>1. Instrument behavior.</b> Log action-family counts, connected house-destination pairs and material use during training. Diagnose which selections prevent trips before changing the objective.')
p('<b>2. Test exploration changes with the same rules.</b> Compare initialization and entropy settings, or a reproducible progression of normal Los Angeles seeds, while retaining all tools and the held-out split. Change one factor at a time.')
p('<b>3. Consider spatial policy changes.</b> A cell-wise action head or better encoding of connectivity may help coordinate endpoints. This is a hypothesis to test, not a promised improvement.')
p('<b>4. Agree before changing the task.</b> Reward shaping, route suggestions, demonstrations or artificial starting states would change the agreed learning setup. They are not present in this checkpoint.')
note('At the measured rate, one million selections would take about <b>1 hour 50 minutes</b> if throughput stayed similar. This is a compute extrapolation, not an estimate of time to a 1,000-trip policy. No longer run was started.')

page(14,'Reproduce and inspect the run','All training code and its documentation live on branch mohammad. Branch main remains the playground. Generated models and logs are local ignored artifacts.')
table(['File / folder','Purpose'],[['training/environment.py','Host protocol, observation encoder, masks, staged actions and reward'],['training/train.py','Network, PPO configuration, time budget, checkpoints and evaluation'],['training/test_environment.py','Seven adapter validation checks'],['output/training/first-full-tools/config.json','Exact revision, packages, seeds and hyperparameters'],['.../episodes.jsonl and progress.csv','Episode outcomes and optimizer measurements'],['.../initial.zip, latest.zip, final.zip','Starting, periodic and final weights; optimizer state'],['.../summary.json','Before/after evaluation, throughput and parameter-change check']],[255,W-255])
sub('Run command used')
p('.venv/Scripts/python.exe training/train.py<br/>  --dotnet ./tmp/dotnet/dotnet.exe<br/>  --minutes 29.5 --steps 65536 --eval-episodes 3<br/>  --output output/training/first-full-tools','CodeX')
p('Source revision: <b>30ef7ab15da7b0452e588cf171ba905ba7121459</b>. The run began from a clean working tree and saved copies of the training source. Packages: PyTorch 2.14.1+cpu, NumPy 2.5.4, Gymnasium 1.4.0, Stable-Baselines3 2.9.2 and SB3-Contrib 2.9.2.')
sub('What was verified')
p('Seven adapter checks passed, including information filtering, reward timing, positive scripted trip rewards, tool command decoding and exact short replays across five maps. The existing 37 simulator suites and ten version/map protocol checks also passed. Checkpoints reloaded both during evaluation and in a separate process.')
p('Decoder fixtures are not proof of arbitrary long learned tool sequences. Simulator tests do not certify parity with the commercial game. Normal OriginalReference fidelity remains unfinished; this model has not been tested against the commercial game.','SmallText')

page(15,'Reference: the exact input layout','This appendix documents the feature interface used by this checkpoint. It is useful when comparing later models or checking whether hidden information leaked into an input.')
table(['Grid channels','Encoding'],[['0','Playable-cell visibility'],['1-3','Terrain categories'],['4-8','Infrastructure categories'],['9-11','Building-kind categories'],['12-19','Building-color categories'],['20-27','Eight road-connection direction bits'],['28','Pending removal'],['29-31','Demand / 20; reservations / 20; overcrowding timer / 50'],['32-39','Eight driveway / entrance directions'],['40-42','Vehicle count / 10; maximum speed / 2; maximum wait / 60'],['43-47','Motorway endpoint; pending retirement; other endpoint x / 50 and y / 30; number / 20'],['48-49','Selected first cell; selected existing motorway endpoint']],[100,W-100])
table(['Global indices','Encoding'],[['0-5','Six inventories: road stock / 100, others / 10'],['6-8','Elapsed time / cap; week / 100; trips / 1000'],['9-24','Two current offers: six type indicators, amount / 100, roads / 100 each'],['25-28','Four selection-phase indicators'],['29-41','Thirteen selected-tool indicators']],[100,W-100])
p('All values are clipped to [0, 1], which can lose magnitude information at high counts. Shared cells and aggregate vehicle statistics can lose entity detail. The raw future schedule, RNG diagnostics and planned building changes are not passed through the encoder. Unknown color IDs, changed grid dimensions or more than two offers raise an error instead of silently truncating the schema.','SmallText')

page(16,'Glossary and evidence sources','Use the source labels below to distinguish measurements from implementation details and general algorithm explanations.')
table(['Term','Meaning in this experiment'],[['Policy / actor','The network distribution used to choose allowed actions'],['Critic / value','A prediction of discounted future trip reward'],['Episode','One game from reset until failure or the external cap'],['Policy selection','One tool or cell choice; not always a completed command'],['Rollout','A batch of 256 recent policy selections'],['Advantage','Estimated outcome relative to what the critic expected'],['Mask','A filter over IDs based on phase, stock and local legality'],['Checkpoint','Saved model and optimizer weights; not a live saved city'],['Held-out seed','A reserved city scenario seed not sampled for training']],[115,W-115])
sub('Measured and implementation evidence')
p('<b>[R1]</b> first-full-tools/summary.json and config.json: experiment contract, before/after evaluation and throughput.<br/><b>[R2]</b> episodes.jsonl: all 242 completed training games. progress.csv: 256 logged rollout rows; last optimizer metrics precede the final update.<br/><b>[R3]</b> Saved final.zip: architecture, 450,610 parameters, 1,024 training epochs and 4,096 Adam steps verified by inspection.<br/><b>[R4]</b> Fresh deterministic replay of seed 2000 for this report: action trace and simulator snapshots; no training.<br/><b>[R5]</b> training/environment.py, training/train.py, training/test_environment.py and simulation/Headless/README.md at the recorded source revision.','SmallText')
sub('Primary algorithm documentation')
p('<b>[R6]</b> Stable-Baselines3 PPO documentation: <link href="https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html" color="#007F82">stable-baselines3.readthedocs.io / PPO</link><br/><b>[R7]</b> OpenAI Spinning Up, PPO: <link href="https://spinningup.openai.com/en/latest/algorithms/ppo.html" color="#007F82">spinningup.openai.com / PPO</link><br/><b>[R8]</b> SB3-Contrib Maskable PPO: <link href="https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html" color="#007F82">sb3-contrib.readthedocs.io / Maskable PPO</link>','SmallText')
p('Documentation checked on 28 October 2026. All graph data is local to the measured run or the explicitly identified checkpoint replay. Hypotheses about future improvements are proposals, not results.','SmallText')

def footer(c,doc):
    c.saveState();c.setStrokeColor(colors.HexColor('#D6E2E7'));c.line(54,51,541,51)
    c.setFillColor(colors.HexColor(GREY));c.setFont('Arial',8)
    c.drawString(54,37,'MOHAMMAD / LOS ANGELES / FIRST CPU EXPERIMENT')
    c.drawRightString(541,37,f'{doc.page:02d}')
    c.restoreState()
doc=SimpleDocTemplate(str(OUT),pagesize=(595.28,841.89),rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=64,
                      title='Inside the Mini Motorways Model - First CPU Training Report',author='Mohammad / Codex',subject='Architecture, reinforcement learning, training graphs and evaluation')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
