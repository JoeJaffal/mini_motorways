using System;using System.Linq;using System.Collections.Generic;using System.Diagnostics;using System.Text.Json;using MotorwaysSim;
class Check{static void Main(){var timer=Stopwatch.StartNew();foreach(bool shared in new[]{false,true})foreach(int seed in new[]{40,41}){
var r=Rules.ForVersion(GameVersion.OriginalReference);r.EnableCityGrowth=false;r.OvercrowdingSeconds=100000;
var w=new TrafficWorld(seed,false,r);w.Reset(seed,ScenarioKind.EmptyLab);w.Inventory[0]=1000;
var shop=shared?w.SpawnSharedCarpark(new Cell(20,10),0):w.SpawnBuilding(new Cell(20,10),0,false);
foreach(var c in new[]{new Cell(5,12),new Cell(5,15),new Cell(5,18),new Cell(5,21)}){var h=w.SpawnBuilding(c,0,true);w.DrawRoad(h.Access,new Cell(10,c.Y));w.DrawRoad(new Cell(10,c.Y),new Cell(10,12));}
w.DrawRoad(new Cell(10,12),shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;shop.NextDemand=1e9;
int concurrent=0;double minParkingDistance=1e9;
for(int tick=0;tick<12000;tick++){if(timer.Elapsed.TotalSeconds>120)throw new Exception("stress wall limit120s");w.Step();concurrent=Math.Max(concurrent,w.Cars.Count(c=>c.Stage==TripStage.EnteringParking||c.Stage==TripStage.LeavingParking));
var moving=w.Cars.Where(c=>c.Moving&&c.CurrentLane.IsParking).ToArray();for(int i=0;i<moving.Length;i++)for(int j=i+1;j<moving.Length;j++)minParkingDistance=Math.Min(minParkingDistance,Point.Distance(moving[i].Position,moving[j].Position));
if(w.TripsCompleted==8&&w.ActiveCars==0)break;}
Console.WriteLine(JsonSerializer.Serialize(new{shared,seed,w.Time,w.TripsCompleted,w.ActiveCars,concurrent,minParkingDistance,waiting=w.Cars.Where(c=>c.Waiting>20).Select(c=>new{c.Id,c.Obstacle,c.Waiting,stage=c.Stage.ToString()}).ToArray(),wall=timer.Elapsed.TotalSeconds}));
}}}
