using System;using System.Linq;
namespace MotorwaysSim {
public static class SharedTransitChecks {
static void Check(bool condition,string message){if(!condition)throw new InvalidOperationException("SHARED TRANSIT: "+message);}
public static int Run(){int checks=0;
foreach(int fixture in new[]{0,1,2}){bool localTraffic=fixture!=0,bent=fixture==2;
var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.OvercrowdingSeconds=100000;
var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);w.Inventory[0]=1000;
var shared=w.SpawnSharedCarpark(new Cell(20,10),1);var far=w.SpawnBuilding(bent?new Cell(24,3):new Cell(32,10),0,false,0,bent?3:0);var home=w.SpawnBuilding(new Cell(5,12),0,true);
w.DrawRoad(home.Access,shared.Entrances[0]);
if(bent){w.DrawRoad(shared.Entrances[1],new Cell(24,12));w.DrawRoad(new Cell(24,12),far.Access);}
else w.DrawRoad(shared.Entrances[1],far.Access);
Check(w.FindRoute(home.Access,far.Access).Count>2,"route may cross unrelated-color shared lot");
var lanes=w.MakeLanes(w.FindRoute(home.Access,far.Access));Check(lanes.Any(l=>l.IsParking&&l.CarparkId==shared.Id),"route expands into actual shared circulation geometry");
for(int i=1;i<lanes.Count;i++)Check(Point.Distance(lanes[i-1].Samples.Last(),lanes[i].Samples[0])<1e-7,"transit joins surface boundaries continuously");
if(localTraffic){foreach(int x in new[]{5,35}){var h=w.SpawnBuilding(new Cell(x,16),1,true);int hub=x==5?10:bent?24:28;w.DrawRoad(h.Access,new Cell(hub,16));w.DrawRoad(new Cell(hub,16),new Cell(hub,12));}}
far.Demand=2;far.DemandCountdown=1e9;shared.Demand=localTraffic?4:0;shared.DemandCountdown=1e9;bool observedOutbound=false,observedReturn=false;
for(int tick=0;tick<12000;tick++){
w.Step();var transit=w.Cars.Where(c=>c.Color==0).ToArray();
foreach(var car in transit){if(car.Moving&&car.CurrentLane.IsParking&&car.CurrentLane.CarparkId==shared.Id){observedOutbound|=car.Stage==TripStage.Outbound;observedReturn|=car.Stage==TripStage.Returning;}Check(!shared.Parking.Contains(car.Id),"transit vehicle never reserves a bay");}
var near=w.Cars.Where(c=>c.Stage!=TripStage.Home&&Point.Distance(c.Position,new Point(shared.Entrance))<5).ToArray();
for(int i=0;i<near.Length;i++)for(int j=i+1;j<near.Length;j++)Check(!w.VehicleBodiesOverlap(near[i].Position,near[i].Heading,near[j].Position,near[j].Heading),"transit/local bodies separated at "+w.Time+" ids="+near[i].Id+","+near[j].Id);
if(w.TripsCompleted==(localTraffic?6:2)&&w.ActiveCars==0)break;
}
Check(observedOutbound&&observedReturn,"vehicles traverse shared lot both outbound and homebound");
Check(far.Served==2&&shared.Served==(localTraffic?4:0)&&w.TripsCompleted==(localTraffic?6:2),"passing through is not a delivery");
Check(w.ActiveCars==0,"mixed queue returns home: "+string.Join(";",w.Cars.Select(c=>c.Id+" "+c.Stage+" "+c.Obstacle+" "+c.Waiting)));
checks++;
}return checks;}
}}
