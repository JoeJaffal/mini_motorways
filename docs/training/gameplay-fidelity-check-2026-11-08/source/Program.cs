using System;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using System.Diagnostics;
using MotorwaysSim;
class Check {
static void Main(){var timer=Stopwatch.StartNew();foreach(int seed in new[]{40,41,42,43}){
var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=100000;
var w=new TrafficWorld(seed,false,rules);var counts=new Dictionary<string,long>();var stages=new Dictionary<string,long>();var rows=new List<object>();
for(int tick=0;tick<8000;tick++){
if(timer.Elapsed.TotalSeconds>120)throw new Exception("120-second wall limit");
if(tick%200==0){w.Inventory[0]=1000;w.BuildReferenceNetwork();}
w.Step();foreach(var c in w.Cars){var st=c.Stage.ToString();stages[st]=stages.GetValueOrDefault(st)+1;if(c.Obstacle!="")counts[c.Obstacle]=counts.GetValueOrDefault(c.Obstacle)+1;}
if((tick+1)%800==0)rows.Add(new{w.Time,w.TripsCompleted,homes=w.Buildings.Count(b=>b.IsHouse),shops=w.Buildings.Count(b=>!b.IsHouse),w.DemandTotal,overCapacity=w.Buildings.Count(b=>!b.IsHouse&&b.Demand>w.DestinationCapacity(b)),upgraded=w.Buildings.Count(b=>b.Upgraded)});
}
Console.WriteLine(JsonSerializer.Serialize(new{seed,w.Time,w.TripsCompleted,vehicleSecondsByObstacle=counts.ToDictionary(k=>k.Key,k=>k.Value*.05),vehicleSecondsByStage=stages.ToDictionary(k=>k.Key,k=>k.Value*.05),rows,wallSeconds=timer.Elapsed.TotalSeconds}));
}}}
