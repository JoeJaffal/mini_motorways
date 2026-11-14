using System;using System.Linq;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{public string Throats()=>string.Join("; ",carparkThroats.Select(t=>$"{t.Key.Item2}->{t.Value}"));
 public string Gate(int id){var c=CarById(id);if(!c.Moving)return "";return string.Join(",",c.Lanes.Skip(c.RouteIndex).Select((l,i)=>TryCarparkGate(c,l,out int lot,out var a,out double d)?$"[{l.Key} d={d:0.000} rank={GateRank(l,d):0.000}]":"").Where(x=>x!=""));}}}
class PFlow{static void Main(){
 int seed=42,layout=2;var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.OvercrowdingSeconds=100000;
 var w=new TrafficWorld(seed,false,rules);w.Reset(seed,ScenarioKind.EmptyLab);w.Inventory[0]=1000;
 var shop=w.SpawnBuilding(new Cell(20,10),0,false,0,layout);var hub=new Cell(20,6);
 for(int i=0;i<4;i++){var cell=new Cell(20+i*3,3);var home=w.SpawnBuilding(cell,0,true);var bend=new Cell(cell.X,hub.Y);w.DrawRoad(home.Access,bend);w.DrawRoad(bend,hub);}
 w.DrawRoad(hub,shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;
 while(w.Time<22.9){w.Step();if(w.Time<22.4)continue;
  Console.WriteLine($"t={w.Time:0.00} throats {w.Throats()}");
  foreach(int id in w.Cars.Where(x=>x.Moving).Select(x=>x.Id)){var c=w.Cars[id];Console.WriteLine($"   car {id} {c.Stage} {(c.Moving?c.CurrentLane.Key:"-")} d={c.DistanceAlongLane:0.000} v={c.Speed:0.000} '{c.Obstacle}' shove={c.Shoving} gates {w.Gate(id)}");}}}}
