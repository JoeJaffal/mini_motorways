import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.env.DECISION_REPO||'C:/Users/moham/mini_motorways';
const archive=path.join(root,'docs/training/review-row-confirmation-2026-11-16');
const out=path.join(root,'outputs/maskable-ppo-reviewed-2026-11-16');
await fs.mkdir(archive,{recursive:true});await fs.mkdir(out,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load('C:/Users/moham/Downloads/Maskable_PPO_Decisions_Clean.xlsx'));
const sheet=wb.worksheets.getItem('Tracker');
const pending=new Set([20,28,47,48,49,51,52,53,54,55,56,57,58]);
const mapping=[];
for(let r=8;r<=58;r++){
 const status=pending.has(r)?'Not reviewed':'Reviewed';
 mapping.push({excelRow:r,id:sheet.getRange(`A${r}`).values[0][0],topic:sheet.getRange(`B${r}`).values[0][0],review:status});
 sheet.getRange(`E${r}`).values=[[status]];
}
wb.recalculate();
assert.equal(mapping.filter(x=>x.review==='Reviewed').length,38);
assert.equal(mapping.filter(x=>x.review==='Not reviewed').length,13);
assert.equal(sheet.getRange('A4').values[0][0],'51 decisions selected. 13 not yet reviewed by you.');
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1000});console.log(errors.ndjson);
for(const [range,name] of [['A1:F15','summary'],['A19:F29','open-topics'],['A46:F58','remaining']]){
 const blob=await wb.render({sheetName:'Tracker',range,scale:1,format:'png'});await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
const target=path.join(out,'Maskable_PPO_Decisions_Reviewed.xlsx');
await(await SpreadsheetFile.exportXlsx(wb)).save(target);await fs.copyFile(target,path.join(archive,'Maskable_PPO_Decisions_Reviewed.xlsx'));
await fs.writeFile(path.join(archive,'review_mapping.json'),JSON.stringify(mapping,null,2)+'\n');
console.log(JSON.stringify({target,reviewed:38,notReviewed:13,pending:[...pending]}));
