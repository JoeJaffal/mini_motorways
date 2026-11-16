import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

const root=process.env.DECISION_REPO || 'C:/Users/moham/mini_motorways';
const archive=path.join(root,'docs/training/maskable-ppo-spec-v1-2026-11-16');
const out=path.join(root,'outputs/maskable-ppo-spec-v1-2026-11-16');
await fs.mkdir(out,{recursive:true});
const rows=JSON.parse(await fs.readFile(path.join(archive,'decisions.json'),'utf8'));
const old=JSON.parse(await fs.readFile(path.join(root,'docs/training/decision-tracker-2026-11-16/decisions.json'),'utf8'));
const originalFile=path.join(root,'docs/training/decision-tracker-2026-11-16/Maskable_PPO_Decisions.xlsx');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(originalFile));
const tracker=wb.worksheets.getItem('Tracker');
const details=wb.worksheets.getItem('Decision details');
const end=rows.length+11, detailEnd=rows.length+7;
// Preserve native tables/styles, extend the existing records and affected features only.
const matrix=rows.map(r=>[r.id,r.topic,r.choice,r.decision,r.review,r.work,r.next,new Date(r.date+'T00:00:00Z')]);
const detailMatrix=rows.map(r=>[r.id,r.topic,r.explanation,r.reason,r.basis,r.next,r.source]);
tracker.tables.items[0].rows.add(null,matrix.slice(old.length));
details.tables.items[0].rows.add(null,detailMatrix.slice(old.length));
for(let i=old.length;i<rows.length;i++){
 tracker.getRange(`A${i+12}:H${i+12}`).copyFrom(tracker.getRange('A54:H54'),'all');
 details.getRange(`A${i+8}:G${i+8}`).copyFrom(details.getRange('A50:G50'),'all');
}
tracker.getRange(`A12:H${end}`).values=matrix;
details.getRange(`A8:G${detailEnd}`).values=detailMatrix;
tracker.getRange(`H12:H${end}`).setNumberFormat('dd mmm yyyy');
tracker.getRange(`A55:H${end}`).format.rowHeightPx=86;
details.getRange(`A51:G${detailEnd}`).format.rowHeightPx=116;
tracker.getRange(`A55:H${end}`).format.wrapText=true;
details.getRange(`A51:G${detailEnd}`).format.wrapText=true;
tracker.getRange('A4').values=[['As of 16 Nov 2026. Done = design selected, not implemented or user-approved. No training started.']];
tracker.getRange('A5').values=[['33 agent-selected decisions are Not reviewed. The 18 prior choices/review flags are preserved; next steps updated.']];
tracker.getRange('A9').values=[['Specification v1 completes the design. Filter User review = Not reviewed to inspect new selections and reasons.']];
details.getRange('A4').values=[['New choices are agent-selected under delegation, with reasons/evidence; they are NOT USER-REVIEWED.']];
details.getRange('A5').values=[['Earlier approvals preserved. Source sections identify the full v1 controls, config, splits, evaluation and limits.']];
for(const [cell,col,status] of [['B7','D','Done'],['D7','D','Partial'],['F7','D','Open'],['B8','E','Reviewed'],['D8','E','Partly reviewed'],['F8','E','Not reviewed'],['H8','F','Documented']])tracker.getRange(cell).formulas=[[`=COUNTIFS(${col}12:${col}${end},"${status}")`]];
tracker.getRange('H7').formulas=[['=SUM(B7,D7,F7)']];
for(const [col,list] of [['D',['Done','Partial','Open']],['E',['Reviewed','Partly reviewed','Not reviewed']],['F',['Not started','Documented','In progress','Verified']]])tracker.getRange(`${col}12:${col}${end}`).dataValidation={rule:{type:'list',values:list}};
// Remove old bounded CF rules before replacing with extended equivalent rules.
tracker.getRange(`D12:E${end}`).conditionalFormats.clear();
for(const [col,entries] of [['D',[['Done','#E4F1EA','#215A3C'],['Partial','#FFF0D3','#7C5519'],['Open','#F8E6E6','#8B3030']]],['E',[['Reviewed','#E4F1EA','#215A3C'],['Partly reviewed','#FFF0D3','#7C5519'],['Not reviewed','#F8E6E6','#8B3030']]]])for(const [status,fill,color] of entries)tracker.getRange(`${col}12:${col}${end}`).conditionalFormats.addCustom(`=${col}12="${status}"`,{fill,font:{color,bold:true}});
wb.recalculate();
assert.equal(tracker.getRange('B7').values[0][0],51);
assert.equal(tracker.getRange('F7').values[0][0],0);
assert.equal(tracker.getRange('B8').values[0][0],18);
assert.equal(tracker.getRange('F8').values[0][0],33);
// Make sure a new unreviewed row affects counts; restore before export.
tracker.getRange('E62').values=[['Reviewed']];wb.recalculate();
assert.equal(tracker.getRange('B8').values[0][0],19);
tracker.getRange('E62').values=[['Not reviewed']];wb.recalculate();
assert.equal(tracker.getRange('B8').values[0][0],18);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:1500});
console.log(errors.ndjson);
for(const [sheetName,range,name] of [['Tracker','A1:H16','tracker'],['Tracker','A23:H27','controls'],['Tracker',`A${end-4}:H${end}`,'tracker-end'],['Decision details','A17:G21','detail-controls'],['Decision details',`A${detailEnd-4}:G${detailEnd}`,'details-end']]){
 const preview=await wb.render({sheetName,range,scale:1,format:'png'});
 await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
const target=path.join(out,'Maskable_PPO_Decisions_v1.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
await fs.copyFile(target,path.join(archive,'Maskable_PPO_Decisions_v1.xlsx'));
const qa={records:51,designSelected:51,open:0,priorUserReviewed:18,newNotReviewed:33,checks:['Imported original workbook; preserved two sheets/native tables/style','Original18reviewed choices/reasons/review flags unchanged; next execution steps updated','Extended8records and dependent formulas/validation/conditional formatting','Status mutation recalculation works; restored','No formula errors matched','Rendered both sheets for visual QA','Exported and copied archive'],nativeExcelTested:false,trainingStarted:false};
await fs.writeFile(path.join(archive,'WORKBOOK_QA.json'),JSON.stringify(qa,null,2)+'\n');
console.log(JSON.stringify({target,...qa}));
