// Diagnostic only: runs a custom scenario (120 s wall cap) and reports (1) home/parked cars whose
// Waiting is non-zero and (2) every car whose Waiting first exceeds 20 s, with its location/obstacle.
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
class WaitProbe{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
var wall=System.Diagnostics.Stopwatch.StartNew();int samples=0;var stale=new List<object>();var longWaits=new List<object>();
var prev=new Dictionary<int,(TripStage stage,double wait,double speed)>();var over=new HashSet<int>();string stop="complete";
try{while(!s.Complete){if(wall.Elapsed.TotalSeconds>120){stop="120s cap";break;}s.AdvanceTick();var w=s.World;
 foreach(var c in w.Cars){
  if(c.Stage==TripStage.Home||c.Stage==TripStage.Parking){samples++;if(c.Waiting>0&&stale.Count<20)stale.Add(new{t=w.Time,c.Id,stage=c.Stage.ToString(),c.Waiting,prev=prev.TryGetValue(c.Id,out var p)?new{stage=p.stage.ToString(),p.wait,p.speed}:null});}
  if(c.Waiting>20&&over.Add(c.Id*100000+(int)(w.Time-c.Waiting)))longWaits.Add(new{t=Math.Round(w.Time,2),c.Id,stage=c.Stage.ToString(),at=new[]{c.At.X,c.At.Y},next=new[]{c.Next.X,c.Next.Y},c.Obstacle,lane=c.Moving?c.CurrentLane.Key:"",c.DistanceAlongLane});
  prev[c.Id]=(c.Stage,c.Waiting,c.Speed);}}}
catch(Exception e){stop="stopped: "+e.Message;}
var W=s.World;Console.WriteLine(JsonSerializer.Serialize(new{stop,time=W.Time,trips=W.TripsCompleted,failed=W.Failed,events=s.CompletedEvents,total=s.Definition.events.Length,homeOrParkedSamples=samples,staleCount=stale.Count,stale,longWaits},opt));}}
