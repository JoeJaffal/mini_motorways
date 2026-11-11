using System;using System.Linq;using MotorwaysSim;
class Eight{static void Main(){
 var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
 var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);w.Inventory[0]=1000;w.Rules.OvercrowdingSeconds=100000;
 var shop=w.SpawnBuilding(new Cell(20,10),0,false);
 foreach(var cell in new[]{new Cell(5,12),new Cell(5,15),new Cell(5,18),new Cell(5,21)}){var home=w.SpawnBuilding(cell,0,true);w.DrawRoad(home.Access,new Cell(10,cell.Y));w.DrawRoad(new Cell(10,cell.Y),new Cell(10,12));}
 w.DrawRoad(new Cell(10,12),shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;
 for(int tick=0;tick<6000;tick++){w.Step();if(w.TripsCompleted==8&&w.ActiveCars==0)break;}
 Console.WriteLine($"t={w.Time:0.0} trips={w.TripsCompleted} active={w.ActiveCars} parking=[{string.Join(",",shop.Parking)}]");
 foreach(var c in w.Cars.Where(c=>c.Stage!=TripStage.Home))Console.WriteLine($"  car {c.Id} {c.Stage} lane {(c.Moving?c.CurrentLane.Key:"-")} d={c.DistanceAlongLane:0.000} v={c.Speed:0.000} wait {c.Waiting:0.0} '{c.Obstacle}' next {string.Join(" ",c.Lanes.Skip(c.RouteIndex+1).Take(2).Select(l=>l.Key))} shove={c.Shoving}");}}
