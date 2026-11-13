/* Exercise the actual viewer script without a browser or npm dependencies.
 * This verifies rendering/control logic; it does not replace visual layout QA.
 */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const template = fs.readFileSync(__dirname + '/viewer.html', 'utf8');
const script = template.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const state = {
  width:50,height:30,time:0,terrain:Array(1500).fill(0),infrastructure:Array(1500).fill(0),
  connections:Array(1500).fill(0),pendingRemovals:Array(1500).fill(0),inventory:[20,1,0,0,1,0],
  tripsCompleted:0,playableXMin:15,playableXMax:35,playableYMin:8,playableYMax:22,
  buildings:[{id:0,color:0,cell:{x:20,y:10},entrance:{x:21,y:10},entrances:[],
    width:1,height:1,isHouse:true,drivewayDirection:0,demand:0}],
  vehicles:[{id:1,color:0,x:21.5,y:10.5,headingX:1,headingY:0,waiting:7,stage:'Outbound'}],
};
state.infrastructure[10*50+21]=1;
const decision = {
  command:'draw',x:21,y:10,toX:22,toY:10,accepted:true,reward:-.52,valuePrediction:12,
  label:'Connect house',components:{trips:0,waitingSeconds:10,modificationCost:4,congestionSeconds:0},
  candidates:[{label:'Connect house',action:{command:'draw'},weight:.75,selected:true},
    {label:'wait',action:{command:'wait'},weight:.25,selected:false}],weightMeaning:'visit share',
};
const session = {meta:{scenario:'DarEsSalaam',seed:200000,mode:'MCTS',runId:'test',
  weights:{alpha:.05,lambdaCost:.005,betaCongestion:0}},status:'Finished',
  main:[{state,decision:null},{state:{...state,time:1},decision}],
  search:[{state:{...state,time:1},decisionIndex:0,simulation:1,depth:1,
    action:decision,reward:-.52,components:decision.components,futureSeed:123}],
};
const elements = new Map();
let draws = 0;
const ctx = new Proxy({}, {get:(target,key)=>target[key]||(()=>{draws++;}),set:(t,k,v)=>(t[k]=v,true)});
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    id,textContent:'',value:'',checked:false,children:[],tagName:'DIV',width:1000,height:600,
    style:{},append(...children){this.children.push(...children);},
    replaceChildren(){this.children=[];},getContext(){return ctx;},
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};},
  });
  return elements.get(id);
}
element('sessionData').textContent=JSON.stringify(session);
for(const [id,value] of Object.entries({waitThreshold:'5',speed:'1',alpha:'.05',lambdaCost:'.005',
  betaCongestion:'0',noteKind:'Penalize',noteTarget:'main'}))element(id).value=value;
for(const id of ['follow','followSearch','focusMap','heat'])element(id).checked=true;
const storage = new Map();
const context = vm.createContext({
  console,document:{getElementById:element,createElement:()=>element('new'+Math.random()),
    activeElement:{tagName:'BODY'},addEventListener(){}},
  localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  requestAnimationFrame(){},setTimeout(){},URL,Blob,
});
vm.runInContext(script,context);
assert.equal(element('clock').textContent,'0.0s');
assert.equal(element('liveControls').hidden,true);
assert(draws>100,'Map drawing did not execute');
element('next').onclick();
assert.equal(element('clock').textContent,'1.0s');
assert.equal(element('action').textContent,'Connect house');
assert.equal(element('return').textContent,'-0.52');
assert.equal(element('waiting').textContent,1);
assert.equal(element('candidates').children.length,2);
element('alpha').value='.2';element('alpha').oninput();
assert.equal(element('return').textContent,'-0.52','Preview mutated the recorded return');
assert.equal(element('rewards').children.at(-1).children[1].textContent,'-2.02');
assert.equal(vm.runInContext('weighted({trips:2,failure:1,unansweredRequestSeconds:4}, {alpha:0,lambdaCost:0,betaCongestion:0,failurePenalty:10,unansweredPenalty:.01})',context),-8.04);
assert.equal(vm.runInContext('weighted({capacityPressureSeconds:3}, {alpha:0,lambdaCost:0,betaCongestion:0,failurePenalty:0,unansweredPenalty:0,overcrowdingPenalty:.05})',context),-.15000000000000002);
element('noteText').value='Repeated construction raised waiting';element('addNote').onclick();
assert.equal(element('annotations').children.length,1);
element('noteTarget').value='search';element('noteText').value='Branch made demand worse';element('addNote').onclick();
const notes=JSON.parse([...storage.values()][0]);
assert.equal(notes.length,2);
assert.equal(notes[1].target,'search');
assert.equal(notes[1].simulation,1);
assert.equal(notes[1].depth,1);
element('mainMap').onclick({clientX:400,clientY:200,target:element('mainMap')});
assert.match(element('inspection').textContent,/MAIN RUN/);
element('prev').onclick();
assert.equal(element('action').textContent,'Initial city');
context.resetEvent={kind:'reset',meta:{...session.meta,runId:'next'},state};
vm.runInContext('applyEvent(resetEvent);render();',context);
assert.equal(element('position').textContent,'Decision 0 / 0');
assert.equal(element('annotations').children.length,0,'Notes leaked into another run');
assert.equal(element('candidates').children.length,0);
assert.equal(vm.runInContext('weighted({trips:2},{tripReward:10,alpha:0,lambdaCost:0,betaCongestion:0,failurePenalty:0,unansweredPenalty:0,overcrowdingPenalty:0})',context),20);
assert.equal(vm.runInContext('weighted({trips:2},{alpha:0,lambdaCost:0,betaCongestion:0,failurePenalty:0,unansweredPenalty:0,overcrowdingPenalty:0})',context),2);
assert.ok(Math.abs(vm.runInContext('weighted({trips:3,clearTripUnits:1.5,congestionFractionSeconds:.5},{tripReward:10,clearTripBonus:.1,congestionFractionPenalty:.02,alpha:0,lambdaCost:0,betaCongestion:0,failurePenalty:0,unansweredPenalty:0,overcrowdingPenalty:0})',context)-30.14)<1e-9);
console.log('PASS: actual viewer script renders frames; seeking; candidate shares; wait highlighting; reward preview isolation; main/search notes; object inspection; episode reset; current/legacy trip multipliers');
