// Diagnostic only. Recomputes each moving car's binding constraint exactly as UpdateVehicles/MayEnter do,
// but records the blocking car, then extracts the deadlocked set (greatest set of stopped cars each held
// by a member). Usage: BlockerProbe scenario.json fromTime toTime everySeconds [wallCap]
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{
public List<(int car,int blocker,string kind,string why,string lane)> Blockers(){
 var snapshot=Cars.Where(c=>c.Moving).Select(c=>new MotionSnapshot{Car=c,Lane=c.CurrentLane,Index=c.RouteIndex,Distance=c.DistanceAlongLane,Speed=c.Speed,Acceleration=c.Acceleration,Position=c.Position}).ToList();
 var result=new List<(int,int,string,string,string)>();
 foreach(var state in snapshot){var car=state.Car;if(car.Speed>=.02)continue;
  double gap=1e6;int leader=-1;
  foreach(var other in snapshot){if(other.Car.Id==car.Id)continue;double distance=double.PositiveInfinity;
   if(other.Lane.Key==state.Lane.Key){double d=other.Distance-state.Distance;if(d>1e-8||Math.Abs(d)<1e-8&&other.Car.Id<car.Id)distance=Math.Max(0,d);}
   else{double ahead=state.Lane.Length-state.Distance;for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++){if(car.Lanes[i].Key==other.Lane.Key){distance=ahead+other.Distance;break;}ahead+=car.Lanes[i].Length;if(ahead>Rules.LookaheadDistance)break;}}
   if(distance<gap){gap=distance;leader=other.Car.Id;}}
  if(leader>=0&&gap-Rules.CarLength-Rules.FollowingGap<.02)result.Add((car.Id,leader,"queue","Queue ahead",state.Lane.Key));
  if(car.Stage==TripStage.Outbound&&car.RouteIndex==car.Lanes.Count-1&&!CarparkThroatAllows(car,state.Lane))result.Add((car.Id,-1,"gate","Carpark entrance merge",state.Lane.Key));
  double aheadDistance=state.Lane.Length-state.Distance;
  for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++){var lane=car.Lanes[i];
   if(aheadDistance<Rules.LookaheadDistance&&!MayEnter(car,lane,snapshot,out string why)){
    bool entrance=lane.IsParking&&lane.Key.Contains(":entrance:")||car.Stage==TripStage.Outbound&&i==car.Lanes.Count-1&&!lane.IsParking;
    double stop=Math.Max(0,aheadDistance-(entrance?Rules.CarLength+.05:Rules.CarLength*.35));
    {int b=-1;string kind="rule";
     foreach(var other in snapshot){if(other.Car.Id==car.Id)continue;if(other.Distance<=other.Lane.Length-Rules.CarLength&&Conflicts(lane,other.Lane)){b=other.Car.Id;kind="conflict";break;}}
     if(b<0&&TryApproach(car,lane.Tile,out _,out double own))foreach(var other in snapshot){
      if(other.Car.Id==car.Id||!TryApproach(other.Car,lane.Tile,out var target,out double theirs))continue;
      if(!Conflicts(lane,target)||!SignalAllows(lane.Tile,target.Incoming))continue;
      bool ownRing=OnTargetRoundabout(car,lane),theirRing=OnTargetRoundabout(other.Car,lane);
      double ownReg=car.ApproachRegistered.TryGetValue(lane.Key,out var t1)?t1:Time,theirReg=other.Car.ApproachRegistered.TryGetValue(target.Key,out var t2)?t2:Time;
      bool priority=theirRing&&!ownRing||theirRing==ownRing&&(theirs<own-1e-6||Math.Abs(theirs-own)<1e-6&&theirReg<ownReg||Math.Abs(theirs-own)<1e-6&&theirReg==ownReg&&other.Car.Id<car.Id);
      if(priority){b=other.Car.Id;kind="priority";break;}}
     result.Add((car.Id,b,kind,why,lane.Key));}
    break;}
   aheadDistance+=lane.Length;if(aheadDistance>Rules.LookaheadDistance)break;}}
 return result;}}}
class BlockerProbe{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
double from=double.Parse(a[1]),to=double.Parse(a[2]),every=double.Parse(a[3]),cap=a.Length>4?double.Parse(a[4]):600,next=from;
var wall=System.Diagnostics.Stopwatch.StartNew();var frames=new List<object>();int firstDeadlock=-1;
while(!s.Complete&&s.World.Time<=to){if(wall.Elapsed.TotalSeconds>cap)break;s.AdvanceTick();var w=s.World;if(w.Time+1e-9<next)continue;next+=every;
 var edges=w.Blockers();var stopped=new HashSet<int>(w.Cars.Where(c=>c.Moving&&c.Speed<.02).Select(c=>c.Id));
 var dead=new HashSet<int>(edges.Where(e=>e.blocker>=0&&stopped.Contains(e.blocker)).Select(e=>e.car));
 bool changed=true;while(changed){changed=false;foreach(var c in dead.ToList())if(!edges.Any(e=>e.car==c&&e.blocker>=0&&dead.Contains(e.blocker))){dead.Remove(c);changed=true;}}
 if(dead.Count>0&&firstDeadlock<0)firstDeadlock=frames.Count;
 frames.Add(new{t=Math.Round(w.Time,2),stopped=stopped.Count,deadlocked=dead.OrderBy(x=>x).ToArray(),
  edges=edges.Select(e=>new{e.car,e.blocker,e.kind,e.why,e.lane,at=new[]{w.Cars[e.car].At.X,w.Cars[e.car].At.Y},stage=w.Cars[e.car].Stage.ToString(),wait=Math.Round(w.Cars[e.car].Waiting,2)}).ToArray()});}
Console.WriteLine(JsonSerializer.Serialize(new{time=s.World.Time,trips=s.World.TripsCompleted,failed=s.World.Failed,firstDeadlockFrame=firstDeadlock,frames},opt));}}
