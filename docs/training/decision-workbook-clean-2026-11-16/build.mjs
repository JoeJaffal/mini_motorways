import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=process.env.DECISION_REPO||'C:/Users/moham/mini_motorways';
const archive=path.join(root,'docs/training/decision-workbook-clean-2026-11-16');
const output=path.join(root,'outputs/maskable-ppo-decisions-clean-2026-11-16');
const source=JSON.parse(await fs.readFile(path.join(root,'docs/training/maskable-ppo-spec-v1-2026-11-16/decisions.json'),'utf8'));
const summaries=[
['Compete with you, then see how far the model can go.','Your goal is human-level play, starting with your own performance.'],
['Explain choices and keep your approval history.','You want to understand and control the design. See D44 for the delegated choices.'],
['Start with new weights, optimizer and learning statistics.','Make a genuinely fresh start without inheriting old training.'],
['Use Maskable PPO.','Your selected approach; the detailed settings are separate choices.'],
['Use the accepted simulator: version f34.','You said its accuracy is sufficient for this project.'],
['Freeze the source and build in a separate branch workspace.','Keep results reproducible and protect existing work.'],
['Build, delete, choose weekly items and wait.','These are the tools you specified.'],
['No generated routes or automatic path completion.','Your strict rule: construction choices belong to the model.'],
['Mask only physically impossible actions.','Keep legal choices available, even when they are poor moves.'],
['Build one neighboring road connection at a time.','Give the model direct control of bends, branches and repairs.'],
['Allow all eight neighboring directions when legal.','You explicitly included diagonal connections.'],
['Build bridges incrementally, like roads on water.','Your reasoning: a bridge is a road on water.'],
['Place a roundabout by choosing its center.','Use the simulator’s native placement and connection rules.'],
['Choose motorway endpoints; allow native editing and removal.','Keep ordinary motorway control and stock behavior.'],
['Allow erasing a connection, tile or entire structure.','Support precise repairs as well as full removal.'],
['Choose from the actual weekly offers while paused.','Do not hide packages or choose an item for the model.'],
['Allow several construction edits during one pause.','You pause to build; each edit returns an updated observation.'],
['Wait one game second, stopping early for a choice or game-over.','Simple timing with frequent chances to react.'],
['Stop a stalled episode after 4,096 decisions without time passing.','Bound endless editing without forced waits or extra penalties.'],
['Select the tool, then its tile and direction or endpoint.','Keep conditional choices manageable without generating routes.'],
['Use one direct policy, without a separate goal selector.','Start with fewer learning components and explicit local control.'],
['Observe structured, visible game information.','Learn gameplay without first needing to recognize screen pixels.'],
['Exclude future spawns, random state and route answers.','Use visible information and leave planning to the model.'],
['Use fixed map channels, global values and motorway pairs.','Represent geography and connections consistently.'],
['Keep four recent traffic observations from different game times.','Distinguish flowing traffic from queues; paused edits add no fake history.'],
['Use game score only.','Your preference. No additional rationale was supplied.'],
['Reward each increase in the game score.','Match the score-only objective without invented bonuses.'],
['Use undiscounted score (gamma 1) and GAE 0.95.','Paused edits should not make later trips worth less.'],
['Train on four cities; reserve London for the final transfer test.','Test new seeds separately and make unseen-city transfer a clear test.'],
['Balance cities and shuffle seeds; no initial curriculum.','Provide variety without adding a second training strategy.'],
['Compare you and the model on 20 matched, first-attempt games.','Measure competition under comparable rules and conditions.'],
['Report score distributions, completion rates and uncertainty.','Avoid judging progress by one lucky game.'],
['Evaluate periodically; choose using a fixed validation cohort.','Make checkpoint selection consistent rather than cherry-picked.'],
['Let you watch the best, worst and an average-scoring game.','You requested direct personal review of the model’s play.'],
['Choose those replays from one frozen model’s evaluation games.','Compare the same policy; select a real game nearest the mean.'],
['Use a small spatial network with separate action and value outputs.','Represent the map while keeping the initial model manageable.'],
['Use the fixed initial PPO settings in the specification.','Start with one interpretable baseline before tuning.'],
['Use pinned software versions and the verified CPU stack.','Make setup and comparisons reproducible.'],
['Use this laptop and the reported Alienware desktop.','These are the machines you said are available.'],
['Start on CPU with two simulator workers; keep runs independent.','Avoid assuming GPU speed gains before measuring the workload.'],
['End at game-over or the one-hour benchmark horizon.','Define a bounded, comparable task with correct ending semantics.'],
['Plan a short pilot; do not launch training automatically.','Check integration before spending time on a longer run.'],
['Keep a durable history, sources and report archive.','You require every material choice and finding to be documented.'],
['Complete the remaining choices, marking them not reviewed.','You delegated the decisions while sleeping, without reviewing them.'],
['Set a defined score-ratio and win-count milestone.','Make “competes with me” measurable; no result is claimed yet.'],
['Add the missing connection-erase, mask and replay integration.','The native core supports erasure, but the adapter needs to expose it.'],
['Freeze development before running final tests.','Keep final-test outcomes from influencing development choices.'],
['Save regular checkpoints and label resumed runs honestly.','Recover from interruptions without claiming exact continuation.'],
['Require integration checks; stop on invalid or nonfinite behavior.','A broken interface must not be interpreted as poor learning.'],
['Measure simulator, input, mask and network costs separately.','Estimate performance from the actual workload, not hardware names.'],
['Keep curriculum, GPU experiments and automatic tuning outside v1.','Make the first experiment interpretable and preserve your strict rules.']
];
assert.equal(source.length,summaries.length);
await fs.mkdir(output,{recursive:true});await fs.mkdir(archive,{recursive:true});
const wb=Workbook.create();
const tracker=wb.worksheets.add('Tracker');
const details=wb.worksheets.add('Decision details');
for(const s of [tracker,details]){s.showGridLines=false;s.tabColor=s===tracker?'#334155':'#94A3B8';}
const end=source.length+7;
tracker.getRange('A2').values=[['Maskable PPO decisions']];
tracker.getRange('A4').formulas=[[`=COUNTA(A8:A${end})&" decisions selected. "&COUNTIFS(E8:E${end},"Not reviewed")&" not yet reviewed by you."`]];
tracker.getRange('A5').values=[['Selected does not mean implemented. Full explanations are on the next tab.']];
const header=['ID','Decision','Choice','Why','Your review','Work'];
tracker.getRange(`A7:F${end}`).values=[header,...source.map((r,i)=>[r.id,r.topic,summaries[i][0],summaries[i][1],r.review,r.work])];
const t=tracker.tables.add(`A7:F${end}`,true,'Decisions');t.style='TableStyleLight1';
details.getRange('A2').values=[['Full explanations']];
details.getRange('A4').values=[['Match the ID on Tracker. These are the original explanations, reasons and sources.']];
details.getRange('A5').values=[['The design and all review statuses are unchanged. This revision only simplifies presentation.']];
details.getRange(`A7:G${end}`).values=[['ID','Decision','Explanation','Reason','Reason supplied by','Next step','Source'],...source.map(r=>[r.id,r.topic,r.explanation,r.reason,r.basis,r.next,r.source])];
const dt=details.tables.add(`A7:G${end}`,true,'DecisionReasons');dt.style='TableStyleLight1';
for(const [s,lastCol,widths] of [[tracker,'F',[50,170,330,290,130,115]],[details,'G',[50,170,390,340,155,310,300]]]){
 const used=s.getRange(`A1:${lastCol}${end}`);used.format.font={name:'Arial',size:11,color:'#273449'};used.format.verticalAlignment='center';
 for(let i=0;i<widths.length;i++)s.getRangeByIndexes(0,i,end,1).format.columnWidthPx=widths[i];
 s.getRange(`A2:${lastCol}2`).format.font={name:'Arial',size:16,bold:true,color:'#172B42'};
 s.getRange(`A3:${lastCol}3`).format.borders={bottom:{style:'thin',color:'#D5DDE5'}};
 s.getRange(`A7:${lastCol}7`).format={fill:'#EEF2F6',font:{name:'Arial',size:11,bold:true,color:'#24364B'},rowHeightPx:32,verticalAlignment:'center',horizontalAlignment:'left'};
 const body=s.getRange(`A8:${lastCol}${end}`);body.format.wrapText=true;body.format.fill='#FFFFFF';body.format.borders={insideHorizontal:{style:'thin',color:'#E8EDF2'}};
 s.freezePanes.freezeRows(7);s.freezePanes.freezeColumns(2);
 for(let i=0;i<source.length;i++){
   const texts=s===tracker?[source[i].id,source[i].topic,...summaries[i],source[i].review,source[i].work]:[source[i].id,source[i].topic,source[i].explanation,source[i].reason,source[i].basis,source[i].next,source[i].source];
   const lines=Math.max(...texts.map((x,j)=>Math.ceil(x.length/Math.max(1,Math.floor((widths[j]-18)/6.5)))));
   s.getRange(`A${i+8}:${lastCol}${i+8}`).format.rowHeightPx=Math.max(s===tracker?52:68,lines*17+14);
 }
}
tracker.getRange(`E8:E${end}`).dataValidation={rule:{type:'list',values:['Reviewed','Not reviewed','Partly reviewed']}};
tracker.getRange(`F8:F${end}`).dataValidation={rule:{type:'list',values:['Not started','Documented','In progress','Verified']}};
tracker.getRange(`E8:E${end}`).conditionalFormats.addCustom('=E8="Not reviewed"',{fill:'#FFF6DF',font:{color:'#77561C'}});
tracker.getRange(`E8:E${end}`).conditionalFormats.addCustom('=E8="Reviewed"',{font:{color:'#47705B'}});
tracker.getRange(`F8:F${end}`).format.font={color:'#657386'};
wb.recalculate();
assert.equal(tracker.getRange('A4').values[0][0],'51 decisions selected. 33 not yet reviewed by you.');
assert.deepEqual(tracker.getRange(`E8:F${end}`).values,source.map(r=>[r.review,r.work]));
tracker.getRange('E8').values=[['Not reviewed']];wb.recalculate();assert.ok(tracker.getRange('A4').values[0][0].includes('34 not yet'));
tracker.getRange('E8').values=[[source[0].review]];wb.recalculate();assert.ok(tracker.getRange('A4').values[0][0].includes('33 not yet'));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1000});console.log(errors.ndjson);
for(const [sheetName,range,name] of [['Tracker','A1:F18','tracker'],['Tracker','A32:F40','settings'],['Tracker',`A${end-5}:F${end}`,'tracker-end'],['Decision details','A1:G11','details']]){
 const b=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(output,name+'.png'),new Uint8Array(await b.arrayBuffer()));
}
const target=path.join(output,'Maskable_PPO_Decisions_Clean.xlsx');await(await SpreadsheetFile.exportXlsx(wb)).save(target);await fs.copyFile(target,path.join(archive,'Maskable_PPO_Decisions_Clean.xlsx'));
await fs.writeFile(path.join(archive,'display_summaries.json'),JSON.stringify(source.map((r,i)=>({id:r.id,choice:summaries[i][0],why:summaries[i][1]})),null,2)+'\n');
await fs.writeFile(path.join(archive,'QA.json'),JSON.stringify({records:51,unreviewed:33,reviewed:18,checks:['All IDs retained','All review/work values preserved','Original full explanation/reason/basis/next/source fields retained on detail sheet','Formula count changes with review status; restored','Formula error scan returned no matches','Both sheets rendered','Exported and archived'],designChanged:false,trainingStarted:false,nativeExcelTested:false},null,2)+'\n');console.log(target);
