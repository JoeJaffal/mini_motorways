using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public static class SimulationChecks
    {
        static void Check(bool value,string message){if(!value)throw new InvalidOperationException("CHECK FAILED: "+message);}
        public static string Run()
        {
            int count=0;
            void Test(string name,Action body){body();count++;}
            Test("terrain, fixed size, original clock",()=>{
                var w=new TrafficWorld(42,false,LegacyFixtureRules());Check(TrafficWorld.Width==50&&TrafficWorld.Height==30,"50 x 30");
                Check(w.Water.Cast<bool>().Count(x=>x)>100,"LA water mask");Check(w.Buildings.Count>=2,"feasible initial shop and household");
                w.Step(400);Check(w.Day==1&&w.Hour==0,"20 second day");w.Step(2400);Check(w.Week==2,"140 second week");
            });
            Test("costs, unlimited inventory, no demolition refunds",()=>{
                var w=Lab();var c=new Cell(10,10);Check(w.Build(BuildTool.Road,c),"road");Check(w.ConstructionSpent==1,"road price");
                Check(!w.Build(BuildTool.Road,c)&&w.ConstructionSpent==1,"invalid build free");
                Check(w.Build(BuildTool.TrafficLight,c)&&w.ConstructionSpent==6,"signal additional price");
                w.Build(BuildTool.Remove,c);Check(w.ConstructionSpent==6&&w.Tile(c)==Infrastructure.None,"demolition");
                w.Water[20,10]=true;Check(w.Build(BuildTool.Bridge,new Cell(20,10))&&w.ConstructionSpent==16,"bridge price per tile");
                var r=new Cell(15,15);Check(w.Build(BuildTool.Roundabout,r)&&w.ConstructionSpent==24,"roundabout price");
                for(int i=0;i<50;i++){w.Build(BuildTool.Remove,r);Check(w.Build(BuildTool.Roundabout,r),"unlimited rings");}
                Check(w.ConstructionSpent==424,"all spending retained");
                Check(!w.Build(BuildTool.Roundabout,new Cell(0,0)),"roundabout footprint bounds");
            });
            Test("explicit links and driveways",()=>{
                var w=Lab();w.Build(BuildTool.Road,new Cell(10,10));w.Build(BuildTool.Road,new Cell(11,10));
                Check(w.FindRoute(new Cell(10,10),new Cell(11,10)).Count==0,"adjacency alone is not a connection");
                Check(w.Connect(new Cell(10,10),new Cell(11,10)),"explicit road link");
                Check(w.FindRoute(new Cell(10,10),new Cell(11,10)).Count==2,"connected route");
                var h=w.SpawnBuilding(new Cell(5,5),0,true);var s=w.SpawnBuilding(new Cell(15,4),0,false);
                ConnectPair(w,h,s);Check(w.FindRoute(h.Access,s.Access).Count>1,"driveway route");
                Check(!w.Build(BuildTool.Road,new Cell(15,5)),"shop footprint protected");
                w.Build(BuildTool.Road,new Cell(5,4));Check(!w.Connect(h.Access,new Cell(5,4)),"house single driveway");
                Check(w.SpawnBuilding(new Cell(6,5),1,true)==null,"future parcels cannot seal existing driveways");
            });
            Test("roundabout circulation is directed",()=>{
                var w=Lab();w.Build(BuildTool.Roundabout,new Cell(15,15));
                var ring=w.Roundabouts[0].Ring;
                Check(w.FindRoute(ring[0],ring[1]).Count==2,"forward ring connection");
                Check(w.FindRoute(ring[1],ring[0]).Count==4,"reverse direction circulates around ring");
                Check(w.Tile(new Cell(15,14))==Infrastructure.Roundabout,"ring uses neighboring tiles");
            });
            Test("reusable trips and functional parking",()=>{
                var w=Pair();w.Step(24000);
                Check(w.TripsCompleted>4,"cars return and are reused: "+Summary(w));
                Check(w.Cars.Count==2,"stable two-car fleet");Check(w.Buildings[1].Reserved>=0,"reservations nonnegative");
                Check(w.Buildings[1].Reserved<=w.Buildings[1].Demand,"reservation bound");
                Check(w.Cars.All(c=>!double.IsNaN(c.Speed)&&c.Speed>=0),"valid kinematics");
            });
            Test("seed determinism and observation isolation",()=>{
                var a=Pair();var b=Pair();a.Step(3000);b.Step(3000);
                Check(a.TripsCompleted==b.TripsCompleted&&a.DemandTotal==b.DemandTotal,"same demand and score");
                for(int i=0;i<a.Cars.Count;i++)Check(a.Cars[i].Position.X==b.Cars[i].Position.X&&a.Cars[i].Position.Y==b.Cars[i].Position.Y,"same vehicle positions");
                var o=a.Observe();o.Vehicles[0].At=new Cell(-1,-1);Check(a.Cars[0].At!=o.Vehicles[0].At,"state detached");
                o.Buildings[1].Parking[0]=999;Check(a.Buildings[1].Parking[0]!=999,"parking detached");
            });
            Test("demand-driven color dispatch",()=>{
                var w=Pair();w.Step(20);Check(w.Cars.All(v=>v.Stage==TripStage.Home),"no demand no departure");
                w.Buildings[1].Color=1;w.Step(300);Check(w.Cars.All(v=>v.Stage==TripStage.Home),"no wrong-color dispatch");
            });
            Test("responsive signal phases and amber",()=>{
                var w=Lab();var c=new Cell(10,10);w.DrawRoad(new Cell(7,10),new Cell(13,10));w.DrawRoad(new Cell(10,7),new Cell(10,13));
                w.Build(BuildTool.TrafficLight,c);var s=w.Signals[c];Check(s.Pairs.Count==2,"opposite approaches paired");
                int initial=s.ActivePair;w.Step(300);Check(s.ActivePair==initial&&!s.Amber,"empty signals do not blindly alternate");
                Check(Math.Abs(w.Rules.SignalGreenSeconds-3)<.001&&Math.Abs(w.Rules.SignalAmberSeconds-.7)<.001,"active inspected timing");
            });
            Test("construction cannot erase a committed return route",()=>{
                var w=Pair();w.Step(300);var car=w.Cars.First(v=>v.Stage!=TripStage.Home);
                var c=car.ReturnRoute.First(p=>w.Tile(p)==Infrastructure.Road);
                int spent=w.ConstructionSpent;w.Build(BuildTool.Remove,c);
                Check(w.PendingRemoval[c.X,c.Y],"return route held");Check(w.ConstructionSpent==spent,"no refund");
            });
            Test("failure only, no artificial horizon",()=>{
                var w=Lab();var h=w.SpawnBuilding(new Cell(5,5),0,true);var s=w.SpawnBuilding(new Cell(15,4),0,false);
                s.Demand=10;s.NextDemand=double.PositiveInfinity;s.SpawnGraceUntil=0;w.Step(2000);Check(w.Failed,"overcrowding fails");
                var empty=Lab();empty.Step(20000);Check(!empty.Failed&&empty.Time==1000,"time alone does not terminate");
            });
            Test("feasibility independent of agent roads",()=>{
                var w=Pair();w.Step(2);double interval=w.Buildings[1].FeasibleDemandInterval;
                Check(w.Buildings[1].FeasibilityVerified&&interval>0,"supporting capacity");
                var c=w.Cars[0].At;w.Build(BuildTool.Remove,new Cell(10,5));w.Step(500);
                Check(Math.Abs(w.Buildings[1].FeasibleDemandInterval-interval)<1e-6,"bad roads do not reduce demand to excuse policy");
            });
            Test("cross traffic, adaptive lights and parking drain",()=>{
                var w=Lab();var h=w.SpawnBuilding(new Cell(10,15),0,true);var s=w.SpawnBuilding(new Cell(28,13),0,false);
                var h2=w.SpawnBuilding(new Cell(20,5),1,true,2);var s2=w.SpawnBuilding(new Cell(20,23),1,false);
                Check(h!=null&&s!=null&&h2!=null&&s2!=null,"crossing parcels");
                w.DrawRoad(h.Access,s.Access);w.DrawRoad(h2.Access,new Cell(20,21));w.DrawRoad(new Cell(20,21),new Cell(19,21));
                w.DrawRoad(new Cell(19,21),new Cell(19,25));w.DrawRoad(new Cell(19,25),s2.Access);w.Build(BuildTool.TrafficLight,new Cell(20,15));
                s.Demand=s2.Demand=6;s.NextDemand=s2.NextDemand=double.PositiveInfinity;
                bool amber=false,parking=false,wait=false;var phases=new HashSet<int>();
                for(int i=0;i<24000&&w.TripsCompleted<12;i++)
                {
                    w.Step();var signal=w.Signals[new Cell(20,15)];amber|=signal.Amber;phases.Add(signal.ActivePair);
                    parking|=w.Cars.Any(v=>v.Stage==TripStage.Parking);wait|=w.Cars.Any(v=>v.WaitingAtSignal);
                    Check(w.Cars.All(v=>!double.IsNaN(v.Position.X)&&!double.IsNaN(v.Speed)),"finite cross traffic");
                    foreach(var shop in new[]{s,s2})foreach(int id in shop.Parking.Where(id=>id>=0))
                        Check(w.Cars[id].ShopId==shop.Id&&w.Cars[id].ParkingSlot>=0,"bay ownership matches vehicle");
                }
                Check(w.TripsCompleted==12,"both crossing streams drain: "+Summary(w));
                Check(amber&&phases.Count==2&&wait,"lights respond to both streams through amber");Check(parking,"functional parking visited");
            });
            Test("gradual city growth and finite state",()=>{
                var a=new TrafficWorld(52,false,LegacyFixtureRules());var b=new TrafficWorld(52,false,LegacyFixtureRules());int initial=a.Buildings.Count;
                a.Step(1000);b.Step(1000);Check(a.Buildings.Count>initial,"houses appear gradually");
                Check(a.Buildings.Count==b.Buildings.Count&&a.Buildings.Zip(b.Buildings,(x,y)=>x.Cell==y.Cell).All(x=>x),"seeded growth repeatable");
                Check(a.Buildings.Where(s=>!s.IsHouse).All(s=>s.FeasibilityVerified),"every spawned shop has terrain-accessible supply");
            });
            Test("color separation diagnostic is physical connectivity only",()=>{
                var w=Pair();var h=w.SpawnBuilding(new Cell(5,18),1,true);var s=w.SpawnBuilding(new Cell(15,17),1,false);
                w.DrawRoad(h.Access,new Cell(14,18));w.DrawRoad(new Cell(14,18),new Cell(14,19));w.DrawRoad(new Cell(14,19),s.Access);
                Check(w.DisconnectedColorComponents()==1,"two separate color service networks detected");
                w.DrawRoad(new Cell(10,5),new Cell(10,18));Check(w.DisconnectedColorComponents()==0,"physical connection removes separation even if unused");
                w.SpawnBuilding(new Cell(35,10),2,true);Check(w.DisconnectedColorComponents()==0,"unserved isolated household is not color segregation");
            });
            Test("two isolated versions and current custom prices",()=>{
                Check(new TrafficWorld(7,false).Rules.Version==GameVersion.OriginalReference,"original target is the default");
                var custom=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.Custom));custom.Reset(7,ScenarioKind.EmptyLab);
                Check(custom.Rules.RoadCost==2&&!custom.Rules.EnforceFeasibility&&custom.Rules.RejectInfeasibleScenarios,"custom settings");
                Check(custom.Build(BuildTool.Road,new Cell(10,10))&&custom.ConstructionSpent==2,"custom road costs two");
                Check(custom.Build(BuildTool.TrafficLight,new Cell(10,10))&&custom.ConstructionSpent==7,"custom light additional five");
                custom.Build(BuildTool.Remove,new Cell(10,10));Check(custom.ConstructionSpent==7,"custom demolition never refunds");
                custom.Water[20,10]=true;custom.Build(BuildTool.Bridge,new Cell(20,10));custom.Build(BuildTool.Roundabout,new Cell(15,15));
                Check(custom.ConstructionSpent==25,"custom bridge ten and roundabout eight");
                var original=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.OriginalReference));original.Reset(7,ScenarioKind.EmptyLab);
                for(int i=0;i<25;i++)Check(original.Build(BuildTool.Road,new Cell(i,10)),"original road stock available");
                Check(!original.Build(BuildTool.Road,new Cell(26,10)),"original inventory is finite");
                original.Build(BuildTool.Remove,new Cell(5,10));Check(original.RoadTilesAvailable==1,"original released road reusable");
                Check(original.ConstructionSpent==0&&original.Rules.ConstructionGraceSeconds==0&&!original.Rules.RejectInfeasibleScenarios,"no custom prices/grace/rejection in original");
                Check(custom.Rules.ConstructionGraceSeconds==30,"custom grace retained");
                original.Step(2800);Check(original.UpgradeChoices.Count>0,"original weekly choices appear");
                int roads=original.Inventory[0];int added=original.UpgradeChoices[0].Roads+(original.UpgradeChoices[0].Type==0?original.UpgradeChoices[0].Amount:0);
                Check(original.ChooseUpgrade(0)&&original.Inventory[0]==roads+added,"original material package applied");
                Check(custom.UpgradeChoices.Count==0,"weekly rewards do not leak to custom");
                var bridge=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.OriginalReference));bridge.Reset(7,ScenarioKind.EmptyLab);
                for(int i=20;i<23;i++){bridge.Water[i,8]=true;Check(bridge.Build(BuildTool.Bridge,new Cell(i,8)),"one bridge supports a water span");}
                Check(bridge.Inventory[0]==22&&bridge.Inventory[1]==0,"span uses three road tiles and one bridge");
                bridge.Build(BuildTool.Remove,new Cell(21,8));bridge.Build(BuildTool.Remove,new Cell(20,8));
                Check(bridge.Inventory[1]==0,"split/removal cannot duplicate bridge stock");
                bridge.Build(BuildTool.Remove,new Cell(22,8));Check(bridge.Inventory[0]==25&&bridge.Inventory[1]==1,"bridge stock returned only after final tile clears");
            });
            Test("infeasible custom scenario rejected instead of demand reduced",()=>{
                var w=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.Custom));w.Reset(7,ScenarioKind.EmptyLab);
                w.SpawnBuilding(new Cell(5,5),0,true);var shop=w.SpawnBuilding(new Cell(40,20),0,false);
                w.Step(500);Check(!w.ScenarioRejected,"grace permits construction before capacity screening");
                Check(shop.FeasibleDemandInterval>shop.OriginalDemandInterval,"test scenario has insufficient estimated capacity");
                w.Step(200);Check(w.ScenarioRejected&&!w.Failed&&w.RejectionReason.Length>0,"rejection separate from agent failure");
                double t=w.Time;w.Step(200);Check(w.Time==t,"rejected scenario must reset");
            });
            Test("same-map and different-map episode options",()=>{
                var seen=new HashSet<ScenarioKind>();
                for(int seed=0;seed<12;seed++){
                    var a=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.Custom));a.Reset(seed,ScenarioKind.LosAngeles,MapVariation.DifferentMaps);seen.Add(a.Scenario);
                    var b=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.Custom));b.Reset(seed,ScenarioKind.LosAngeles,MapVariation.DifferentMaps);
                    Check(a.Scenario==b.Scenario&&a.Buildings.Count==b.Buildings.Count,"map variation is seed-repeatable");
                    Check(a.Buildings.Count>=2,"selected map has initial household and shop");
                    a.Reset(seed,ScenarioKind.Tokyo,MapVariation.SameMap);Check(a.Scenario==ScenarioKind.Tokyo,"same map stays selected");
                }
                Check(seen.Count==3,"variation actually samples three recovered maps");
            });
            return $"PASS: {count} simulation suites. Tests cover custom rules, recovered constants/structures, and integration; they do not prove bit-identical parity.\n";
        }

        static Rules LegacyFixtureRules()=>new Rules {RoadCost=1,EnforceFeasibility=true,RejectInfeasibleScenarios=false,EnableCityGrowth=true};
        public static TrafficWorld Lab()=>new TrafficWorld(42,true,LegacyFixtureRules()) is TrafficWorld w?ResetLab(w):null;
        static TrafficWorld ResetLab(TrafficWorld w){w.Reset(42,ScenarioKind.EmptyLab);return w;}
        public static TrafficWorld Pair()
        {
            var w=Lab();var house=w.SpawnBuilding(new Cell(5,5),0,true);var shop=w.SpawnBuilding(new Cell(15,4),0,false);
            ConnectPair(w,house,shop);return w;
        }
        public static void ConnectPair(TrafficWorld w,Building house,Building shop)
        {
            w.DrawRoad(house.Access,new Cell(14,5));w.DrawRoad(new Cell(14,5),new Cell(14,6));w.DrawRoad(new Cell(14,6),shop.Access);
        }
        public static string Summary(TrafficWorld w)=>$"time={w.Time:0.0}, trips={w.TripsCompleted}, demand={w.DemandTotal}, failed={w.Failed}; "+
            string.Join(" | ",w.Cars.Select(c=>$"{c.Id} {c.Stage} {c.At} lane={c.RouteIndex}/{c.Lanes.Count} x={c.Position.X:0.00} speed={c.Speed:0.000} {c.Obstacle}"));
    }
}
