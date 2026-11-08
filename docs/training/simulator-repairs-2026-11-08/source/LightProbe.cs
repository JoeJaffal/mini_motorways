// Diagnostic only: replays AI recordings and measures traffic-light phase behaviour each tick.
// "blocked switch" = another pair is preferred but the switch is refused because 1..(min-1) green cars are
// within the nearby distance; "stuck" = the same, with every one of those nearby green cars stopped.
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{
 public readonly Dictionary<string,double> StuckReasons=new Dictionary<string,double>();
 public (bool blocked,bool stuck,int red) LightState(SignalState s){
  if(s.Amber)return(false,false,0);
  var cands=SignalCandidates(s.Cell);int nearbyCount=NearbyCount(s,cands);int red=0;
  foreach(var c in Cars){if(!TryApproach(c,s.Cell,out var lane,out double d))continue;if((s.ActivePair&(1<<((lane.Incoming+4)%8)))==0&&c.Obstacle=="Traffic light")red++;}
  var near=cands.Where(c=>(s.ActivePair&(1<<c.Approach))!=0&&c.Distance<Rules.SignalNearbyDistance).Select(c=>c.Car).ToList();
  bool blocked=WinningPair(s,cands,false)!=s.ActivePair&&nearbyCount>0&&nearbyCount<Rules.SignalMinimumNearbyCars;
  bool stuck=blocked&&near.All(c=>c.Speed<.02);if(stuck)foreach(var c in near){var k=c.Obstacle==""?"(none)":c.Obstacle;StuckReasons[k]=StuckReasons.GetValueOrDefault(k)+Rules.TickSeconds;}
  return(blocked,stuck,red);}
 public bool FewLanes(Cell c)=>ChunkHasFewLanes(c);}}
class LightProbe{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true,Converters={new System.Text.Json.Serialization.JsonStringEnumConverter()}};
var results=new List<object>();
foreach(var path in a){
 var rec=JsonSerializer.Deserialize<AiReplayRecording>(File.ReadAllText(path),opt);var s=new AiReplaySession(rec);var w=s.World;double dt=w.Rules.TickSeconds;
 var stuck=new Dictionary<Cell,double>();var blocked=new Dictionary<Cell,double>();var longest=new Dictionary<Cell,double>();var run=new Dictionary<Cell,double>();var redWait=new Dictionary<Cell,double>();
 double lightWait=0,allWait=0;int ticks=0;
 while(!s.Complete){s.AdvanceTick();ticks++;
  foreach(var c in w.Cars)if(c.Moving&&c.Speed<.02){allWait+=dt;if(c.Obstacle=="Traffic light")lightWait+=dt;}
  foreach(var sig in w.Signals.Values){var st=w.LightState(sig);var k=sig.Cell;
   if(st.blocked)blocked[k]=blocked.GetValueOrDefault(k)+dt;
   if(st.stuck){stuck[k]=stuck.GetValueOrDefault(k)+dt;run[k]=run.GetValueOrDefault(k)+dt;longest[k]=Math.Max(longest.GetValueOrDefault(k),run[k]);redWait[k]=redWait.GetValueOrDefault(k)+st.red*dt;}else run[k]=0;}}
 results.Add(new{file=Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(path)))+"/"+Path.GetFileName(path),simulatorVersion=SimulatorVersion.Value,score=w.TripsCompleted,seconds=Math.Round(w.Time,2),
  lights=w.Signals.Keys.Select(k=>new{cell=new[]{k.X,k.Y},fewLanes=w.FewLanes(k),blockedSwitchSeconds=Math.Round(blocked.GetValueOrDefault(k),2),stuckSeconds=Math.Round(stuck.GetValueOrDefault(k),2),longestStuckSeconds=Math.Round(longest.GetValueOrDefault(k),2),redCarSecondsWhileStuck=Math.Round(redWait.GetValueOrDefault(k),1)}).ToArray(),
  carSecondsStoppedAtRedLight=Math.Round(lightWait,1),stuckGreenCarReasons=w.StuckReasons.ToDictionary(x=>x.Key,x=>Math.Round(x.Value,1)),carSecondsStoppedTotal=Math.Round(allWait,1)});}
Console.WriteLine(JsonSerializer.Serialize(results,new JsonSerializerOptions{WriteIndented=false}));}}
