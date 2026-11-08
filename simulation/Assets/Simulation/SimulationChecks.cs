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
            int count=GameplayFidelityChecks.Run()+CustomScenarioChecks.Run()+ParkingFlowChecks.Run()+RecordedCarparkChecks.Run()+SharedTransitChecks.Run();
            void Test(string name,Action body){body();count++;}
            Test("AI command replay reproduces normal-play transitions",()=>{
                var world=new TrafficWorld(42,false,Rules.ForVersion(GameVersion.OriginalReference));
                world.Reset(42,ScenarioKind.LosAngeles);
                Cell built=new Cell(-1,-1);
                for(int y=0;y<TrafficWorld.Height&&built.X<0;y++)for(int x=0;x<TrafficWorld.Width;x++)
                    if(world.Build(BuildTool.Road,new Cell(x,y))){built=new Cell(x,y);break;}
                Check(built.X>=0,"normal stock can build a road");world.Step(20);
                var first=new AiReplayAction{command="build",tool="Road",x=built.X,y=built.Y,ticks=20,accepted=true,afterTrips=world.TripsCompleted,afterTime=world.Time};
                world.Step(20);
                var wait=new AiReplayAction{command="wait",ticks=20,accepted=true,afterTrips=world.TripsCompleted,afterTime=world.Time};
                Check(!world.DrawRoad(new Cell(-1,-1),new Cell(0,0)),"invalid stroke rejected");world.Step(20);
                var invalid=new AiReplayAction{command="draw",x=-1,y=-1,toX=0,toY=0,ticks=20,accepted=false,afterTrips=world.TripsCompleted,afterTime=world.Time};
                var recording=new AiReplayRecording{schemaVersion=1,version="OriginalReference",scenario="LosAngeles",variation="SameMap",seed=42,
                    score=world.TripsCompleted,duration=world.Time,actions=new[]{first,wait,invalid}};
                var session=new AiReplaySession(recording);while(!session.Complete)session.AdvanceTick();
                Check(session.World.Inventory.SequenceEqual(world.Inventory)&&session.World.Observe().Connections.SequenceEqual(world.Observe().Connections),"replay materials and connections match");
                Check(session.CompletedCommands==3,"commands completed including wait and rejection");
                session.AdvanceTick();Check(session.CompletedCommands==3,"completed replay does not advance");
                first.afterTrips++;bool rejected=false;
                try{session=new AiReplaySession(recording);while(!session.Complete)session.AdvanceTick();}catch(InvalidOperationException){rejected=true;}
                Check(rejected,"tampered outcome detected");
            });
            Test("AI replay refuses helpers and wrong versions",()=>{
                var recording=new AiReplayRecording{schemaVersion=1,version="OriginalReference",scenario="LosAngeles",variation="SameMap",seed=42,
                    actions=new[]{new AiReplayAction{command="reference",ticks=20,accepted=true}}};
                bool rejected=false;
                try{new AiReplaySession(recording).AdvanceTick();}catch(ArgumentException){rejected=true;}
                Check(rejected,"privileged command refused");recording.version="Custom";rejected=false;
                try{new AiReplaySession(recording);}catch(ArgumentException){rejected=true;}
                Check(rejected,"version boundary enforced");
            });
            Test("useful connectivity counts matching round trips once without gameplay mutation",()=>{
                var w=Pair();var home=w.Buildings.First(b=>b.IsHouse);var shop=w.Buildings.First(b=>!b.IsHouse);
                var before=w.Observe();int version=w.NetworkVersion;
                Check(w.UsefulConnectedHouseCount()==1&&w.UsefulConnectedHouseCount()==1,"one productive house, cached query");
                Check(w.Observe().Connections.SequenceEqual(before.Connections)&&w.Inventory.SequenceEqual(before.Inventory)&&
                    w.NetworkVersion==version&&w.Time==before.Time&&w.TripsCompleted==0,"diagnostic does not build, score or step");
                w.SpawnBuilding(new Cell(5,9),1,true);w.DrawRoad(new Cell(5,9),new Cell(10,9));w.DrawRoad(new Cell(10,9),new Cell(10,5));
                Check(w.UsefulConnectedHouseCount()==1,"wrong-color connection adds no house credit");
                w.SetHouseDriveway(home.Id,6);Check(w.UsefulConnectedHouseCount()==0,"detached driveway invalidates cached count");
                w.SetHouseDriveway(home.Id,0);Check(w.UsefulConnectedHouseCount()==1,"reconnected driveway restores count");
                w.Build(BuildTool.Remove,new Cell(10,5));
                Check(w.UsefulConnectedHouseCount()==0,"pending/deleted connection not credited");
                w.Reset(42,ScenarioKind.EmptyLab);Check(w.UsefulConnectedHouseCount()==0,"reset invalidates query cache");
                w=Pair();home=w.Buildings.First(b=>b.IsHouse);shop=w.Buildings.First(b=>!b.IsHouse);
                // Diagnostic directed fixture: outbound link exists but return does not.
                w.Connections[6,5]&=~(1<<4);w.Build(BuildTool.Road,new Cell(25,20));
                Check(w.BestRouteTo(home.Access,shop).Count>1&&w.FindRoute(shop.Access,home.Access).Count==0,"one-way fixture");
                Check(w.UsefulConnectedHouseCount()==0,"outbound-only connection earns no credit");
            });
            Test("draw-change diagnostic rejects only physically unchanged strokes",()=>{
                var w=Pair();var from=new Cell(6,5);var to=new Cell(14,5);
                int version=w.NetworkVersion;var before=w.Observe();
                Check(!w.DrawMayChange(from,to),"existing connected stroke is a no-op");
                Check(w.DrawMayChange(from,new Cell(10,8)),"new road extension remains available");
                Check(w.DrawMayChange(new Cell(5,5),new Cell(5,8)),"house driveway rotation remains available");
                var choices=w.DrawChangeChoices(from);
                Check(choices.Length==TrafficWorld.Width*TrafficWorld.Height&&!choices[to.Y*TrafficWorld.Width+to.X],"batched diagnostic");
                Check(w.NetworkVersion==version&&w.Observe().Connections.SequenceEqual(before.Connections),"query is read-only");
                int checkedNoops=0;
                foreach(var start in new[]{new Cell(5,5),from,new Cell(10,5),new Cell(14,6),new Cell(15,6)})
                    for(int y=3;y<10;y++)for(int x=4;x<18;x++)
                    {
                        var end=new Cell(x,y);if(w.DrawMayChange(start,end))continue;
                        var snapshot=w.Observe();int direction=w.Buildings[0].DrivewayDirection;
                        w.DrawRoad(start,end);checkedNoops++;
                        Check(w.Observe().Connections.SequenceEqual(snapshot.Connections)&&w.Observe().Infrastructure.SequenceEqual(snapshot.Infrastructure)&&
                            w.Inventory.SequenceEqual(snapshot.Inventory)&&w.Buildings[0].DrivewayDirection==direction,"no false no-op classification");
                    }
                Check(checkedNoops>10,"multiple no-op geometries checked");
            });
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
            Test("roads reaching visible driveways dispatch cars",()=>{
                foreach(var version in new[]{GameVersion.OriginalReference,GameVersion.Custom})
                {
                    var rules=Rules.ForVersion(version);rules.EnableCityGrowth=false;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                    var home=w.SpawnBuilding(new Cell(5,5),0,true);
                    var shop=w.SpawnBuilding(new Cell(15,4),0,false);
                    // Start and finish outside the parcels, at the visible driveway ends.
                    w.DrawRoad(new Cell(6,5),new Cell(14,5));w.DrawRoad(new Cell(14,5),new Cell(14,6));
                    Check(w.FindRoute(home.Access,shop.Access).Count>1,"driveway ends attach to new roads: "+version);
                    Check(w.FindRoute(shop.Access,home.Access).Count>1,"driveways attach in both directions");
                    Check(w.FindRoute(home.Access,new Cell(5,4)).Count==0,"unrelated parcel sides stay disconnected");
                    shop.Demand=1;w.Step(4000);
                    Check(w.TripsCompleted>0,"connected driveway dispatches and delivers: "+version+" "+Summary(w));
                }
            });
            Test("house driveway can be redirected by drawing",()=>{
                var w=Lab();var home=w.SpawnBuilding(new Cell(5,5),0,true);
                w.Build(BuildTool.Road,new Cell(6,5));
                Check(w.DrawRoad(home.Cell,new Cell(5,7)),"draw from house toward new exit");
                Check(home.DrivewayDirection==2&&w.FindRoute(home.Cell,new Cell(5,7)).Count==3,"new exit works");
                Check(w.FindRoute(home.Cell,new Cell(6,5)).Count==0,"old driveway detached");
                w.Water[4,5]=true;Check(!w.SetHouseDriveway(home.Id,4)&&home.DrivewayDirection==2,"water rejected without changing exit");
                w.SpawnBuilding(new Cell(4,4),1,true);Check(!w.SetHouseDriveway(home.Id,5),"occupied neighbor rejected");
                Check(w.SetHouseDriveway(home.Id,1)&&home.DrivewayDirection==1,"diagonal exit supported");
            });
            Test("retiring driveway pavement is display only and clears after committed trips",()=>{
                var w=Lab();var home=w.SpawnBuilding(new Cell(5,5),0,true);var exit=new Cell(6,5);
                w.Build(BuildTool.Road,exit);
                var car=w.Cars.First(c=>c.HomeId==home.Id);
                car.Stage=TripStage.Outbound;car.Lanes=w.MakeLanes(new[]{home.Cell,exit});
                car.ReturnRoute=new List<Cell>{exit,home.Cell};
                Check(w.RetiringRoadLinks().Count==0,"live links need no retiring pavement");
                Check(w.SetHouseDriveway(home.Id,2),"redirect while trip committed");
                var before=w.Observe();int spent=w.ConstructionSpent,version=w.NetworkVersion;
                var links=w.RetiringRoadLinks();
                Check(links.Count==1&&((links[0].From==home.Cell&&links[0].To==exit)||
                    (links[0].To==home.Cell&&links[0].From==exit)),"old committed driveway retained once");
                Check(w.FindRoute(home.Cell,exit).Count==0,"display does not reopen old driveway");
                Check(w.Observe().Connections.SequenceEqual(before.Connections)&&
                    w.Inventory.SequenceEqual(before.Inventory)&&w.ConstructionSpent==spent&&w.NetworkVersion==version,
                    "display query does not mutate network or materials");
                car.Stage=TripStage.Home;
                Check(w.RetiringRoadLinks().Count==0,"pavement disappears when committed trip finishes");
            });
            Test("Original roundabout conversion conserves replaced concrete",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                var w=new TrafficWorld(40,false,rules);w.Reset(40,ScenarioKind.EmptyLab);
                int startingRoads=w.Inventory[0];w.Inventory[4]=1;var center=new Cell(15,15);
                foreach(var c in new[]{center,new Cell(15,14),new Cell(14,15),new Cell(15,16),new Cell(16,15)})
                    Check(w.Build(BuildTool.Road,c),"prepare five replaced roads");
                Check(w.Inventory[0]==startingRoads,"unconnected markers spend no concrete");
                foreach(var c in new[]{new Cell(15,14),new Cell(14,15),new Cell(15,16),new Cell(16,15)})Check(w.Connect(center,c),"connect footprint roads");
                Check(w.Inventory[0]==startingRoads-4,"four ordinary connections spent");
                for(int i=0;i<3;i++)
                {
                    Check(w.Build(BuildTool.Roundabout,center),"convert or rebuild unused circle");
                    Check(w.Inventory[0]==startingRoads,"replaced roads refunded once");
                    w.Step(2);Check(w.Inventory[0]==startingRoads,"no repeated refund on ticks");
                    Check(w.Build(BuildTool.Remove,center),"remove unused circle");
                    Check(w.Inventory[0]==startingRoads&&w.Inventory[4]==1,"stocks conserved after removal");
                }
            });
            Test("Original roundabout concrete waits for committed surface paths",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                var home=w.SpawnBuilding(new Cell(5,10),0,true);var shop=w.SpawnBuilding(new Cell(18,8),0,false);
                Check(w.DrawRoad(home.Access,shop.Access),"prepare occupied road");
                shop.DemandCountdown=1e9;shop.NextDemand=1e9;shop.Demand=1;w.Step(1);
                var center=new Cell(11,10);int before=w.Inventory[0];w.Inventory[4]=1;
                Check(w.Cars.Any(v=>v.Moving&&v.Lanes.Any(l=>l.Tile==center)),"old path crosses footprint");
                Check(w.Build(BuildTool.Roundabout,center),"convert occupied road");
                int replaced=w.Roundabouts[0].ReplacedRoadTiles;
                Check(replaced==4&&w.Inventory[0]==before,"hold concrete for four replaced connections");
                Check(w.Build(BuildTool.Remove,center),"queue occupied circle removal");
                w.Step(6000);
                Check(w.Inventory[0]==before+replaced&&w.Inventory[4]==1&&w.Roundabouts.Count==0,
                    "refund old concrete and circle exactly once after traffic clears");
            });
            Test("roundabout circulation is directed",()=>{
                var w=Lab();w.Build(BuildTool.Roundabout,new Cell(15,15));
                var ring=w.Roundabouts[0].Ring;
                Check(w.FindRoute(ring[0],ring[1]).Count==2,"forward ring connection");
                Check(w.FindRoute(ring[1],ring[0]).Count==4,"reverse direction circulates around ring");
                Check(w.Tile(new Cell(15,14))==Infrastructure.Roundabout,"ring uses neighboring tiles");
            });
            Test("roundabout conversion accepts committed moving traffic",()=>{
                foreach(var version in new[]{GameVersion.OriginalReference,GameVersion.Custom})
                {
                    var rules=Rules.ForVersion(version);rules.EnableCityGrowth=false;rules.RejectInfeasibleScenarios=false;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                    var home=w.SpawnBuilding(new Cell(5,10),0,true);
                    var shop=w.SpawnBuilding(new Cell(18,8),0,false);
                    w.DrawRoad(home.Access,shop.Access);shop.DemandCountdown=1e9;shop.NextDemand=1e9;shop.Demand=1;
                    var center=new Cell(11,10);w.Inventory[4]=1;
                    for(int i=0;i<1000&&!w.Cars.Any(c=>c.Moving);i++)w.Step();
                    Check(w.Cars.Any(c=>c.Moving&&c.Lanes.Any(l=>l.Tile==center)),"trip committed through conversion site");
                    Check(w.Build(BuildTool.Roundabout,center),"place during active trip: "+version+" "+w.LastAction);
                    Check(w.FindRoute(home.Access,shop.Access).All(c=>c!=center),"new routes avoid roundabout center");
                    w.Step(6000);
                    Check(w.TripsCompleted>=1&&w.Cars.All(c=>c.Stage==TripStage.Home),"committed traffic delivers and returns: "+version+" "+Summary(w));
                }
            });
            Test("roundabout circulating lanes share a circular centreline",()=>{
                var w=Lab();w.Build(BuildTool.Roundabout,new Cell(15,15));var ring=w.Roundabouts[0].Ring;
                var lanes=w.MakeLanes(ring.Concat(new[]{ring[0],ring[1]}).ToList());
                for(int i=1;i<5;i++)
                {
                    foreach(var p in lanes[i].Samples)Check(Math.Abs(Point.Distance(p,new Point(new Cell(15,15)))-TrafficWorld.RoundaboutLaneRadius)<1e-8,"circle radius");
                    if(i<4)Check(Point.Distance(lanes[i].Samples.Last(),lanes[i+1].Samples[0])<1e-8,"continuous quadrant joins");
                }
            });
            Test("roundabout conversion clears a platoon from multiple approaches",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.OvercrowdingSeconds=100000;
                var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                var center=new Cell(15,15);
                foreach(var cell in new[]{new Cell(10,15),new Cell(20,15),new Cell(15,10)})
                {var home=w.SpawnBuilding(cell,0,true);w.DrawRoad(home.Access,center);}
                var shop=w.SpawnBuilding(new Cell(14,20),0,false,0,2);
                w.DrawRoad(center,new Cell(15,19));w.DrawRoad(new Cell(15,19),new Cell(14,19));w.DrawRoad(new Cell(14,19),shop.Access);
                shop.Demand=6;shop.DemandCountdown=1e9;shop.NextDemand=1e9;w.Step(100);w.Inventory[4]=1;
                Check(w.ActiveCars==6&&w.Build(BuildTool.Roundabout,center),"six active trips during conversion");
                w.Step(20000);
                Check(w.TripsCompleted==6&&w.ActiveCars==0,"platoon delivers and returns without locking: "+Summary(w));
            });
            Test("adjacent city junctions release crossing reservations",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=100000;
                var w=new TrafficWorld(42,false,rules);
                int recentTrips=0;
                for(int i=0;i<8000;i++){if(i==7200)recentTrips=w.TripsCompleted;if(i%200==0){w.Inventory[0]=1000;w.BuildReferenceNetwork();}w.Step();}
                Check(w.TripsCompleted>recentTrips,"connected city continues delivering in final40seconds: "+w.TripsCompleted);
                Check(!w.Cars.Any(c=>c.Waiting>20&&(c.Obstacle=="Crossing vehicle"||c.Obstacle=="Approaching vehicle priority")),"no persistent crossing reservation cycle: "+Summary(w));
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
                for(int i=0;i<26;i++){Check(original.Build(BuildTool.Road,new Cell(i,10)),"road node available");if(i>0)Check(original.Connect(new Cell(i-1,10),new Cell(i,10)),"paid ordinary connection");}
                Check(original.Build(BuildTool.Road,new Cell(26,10))&&!original.Connect(new Cell(25,10),new Cell(26,10)),"original connection inventory is finite");
                original.Build(BuildTool.Remove,new Cell(5,10));Check(original.RoadTilesAvailable==2,"both incident connections refunded");
                Check(original.ConstructionSpent==0&&original.Rules.ConstructionGraceSeconds==0&&!original.Rules.RejectInfeasibleScenarios,"no custom prices/grace/rejection in original");
                Check(custom.Rules.ConstructionGraceSeconds==30,"custom grace retained");
                original.Step(2800);Check(original.UpgradeChoices.Count>0,"original weekly choices appear");
                int roads=original.Inventory[0];int added=original.UpgradeChoices[0].Roads+(original.UpgradeChoices[0].Type==0?original.UpgradeChoices[0].Amount:0);
                Check(original.ChooseUpgrade(0)&&original.Inventory[0]==roads+added,"original material package applied");
                Check(custom.UpgradeChoices.Count==0,"weekly rewards do not leak to custom");
                var bridge=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.OriginalReference));bridge.Reset(7,ScenarioKind.EmptyLab);
                for(int i=20;i<23;i++){bridge.Water[i,8]=true;Check(bridge.Build(BuildTool.Bridge,new Cell(i,8)),"one bridge supports a water span");}
                Check(bridge.Connect(new Cell(20,8),new Cell(21,8))&&bridge.Connect(new Cell(21,8),new Cell(22,8)),"connect water span");
                Check(bridge.Inventory[0]==23&&bridge.Inventory[1]==0,"span uses two connections and one bridge");
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
                for(int seed=0;seed<32;seed++){
                    var a=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.Custom));a.Reset(seed,ScenarioKind.LosAngeles,MapVariation.DifferentMaps);seen.Add(a.Scenario);
                    var b=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.Custom));b.Reset(seed,ScenarioKind.LosAngeles,MapVariation.DifferentMaps);
                    Check(a.Scenario==b.Scenario&&a.Buildings.Count==b.Buildings.Count,"map variation is seed-repeatable");
                    Check(a.Buildings.Count>=2,"selected map has initial household and shop");
                    a.Reset(seed,ScenarioKind.Tokyo,MapVariation.SameMap);Check(a.Scenario==ScenarioKind.Tokyo,"same map stays selected");
                }
                Check(seen.Count==CityCatalog.Maps.Length,"variation samples all five recovered maps");
            });
            Test("five reference profiles, complete color groups and expansion",()=>{
                Check(CityCatalog.Maps.Length==5,"five requested maps");
                Check(CityCatalog.Get(ScenarioKind.Tokyo).BaseDemand.Length==6,"Tokyo sixth color retained");
                foreach(var scenario in CityCatalog.Maps)
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                    for(int seed=0;seed<5;seed++)
                    {
                        var w=new TrafficWorld(seed,false,rules);w.Reset(seed,scenario);
                        Check(w.Buildings.Count>=2,scenario+" initial destination and supply seed "+seed);
                        Check(w.Buildings.All(b=>w.IsPlayable(b.Cell)&&w.IsPlayable(new Cell(b.Cell.X+b.Width-1,b.Cell.Y+b.Height-1))),"spawn fits active city");
                        double[] before=w.PlayableBounds;w.Step(100);Check(w.CityZoom>=w.Map.Zoom[0],"valid zoom");
                        Check(!w.IsPlayable(new Cell(0,0)),"outside starting playable area");
                        Check(!w.Build(BuildTool.Road,new Cell(0,0)),"construction outside active city rejected");
                    }
                }
                var tokyo=new TrafficWorld(5,false,Rules.ForVersion(GameVersion.Custom));tokyo.Reset(5,ScenarioKind.EmptyLab);
                Check(tokyo.SpawnBuilding(new Cell(5,5),5,true)==null,"LA does not have an orange group");
                tokyo.Reset(5,ScenarioKind.Tokyo);Check(tokyo.Map.HouseZones.Length==6&&tokyo.Map.ShopZones.Length==6,"all Tokyo zones exported");
            });
            Test("original motorway routing, continuous lanes and safe removal",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                var w=new TrafficWorld(7,false,rules);w.Reset(7,ScenarioKind.EmptyLab);
                var house=w.SpawnBuilding(new Cell(5,5),0,true);var shop=w.SpawnBuilding(new Cell(30,4),0,false);
                Cell start=new Cell(6,5),end=new Cell(29,6);
                Check(!w.AddMotorway(start,end),"motorway cannot be built without stock");w.Inventory[2]=1;
                for(int y=0;y<TrafficWorld.Height;y++)w.Water[20,y]=true;
                Check(w.AddMotorway(start,end),"motorway spans water without surface bridge");
                Check(w.Inventory[2]==0&&w.Inventory[0]==25,"standard motorway uses one motorway and no concrete");
                Check(w.Connect(house.Access,start)&&w.Connect(end,shop.Access),"endpoints connect to driveways");
                var path=w.FindRoute(house.Access,shop.Access);Check(path.Count==4,"route uses two remote motorway endpoints");
                Check(w.FindRoute(new Cell(20,4),new Cell(20,6)).Count==0,"span does not create ground junctions");
                var lanes=w.MakeLanes(path);Check(lanes.Any(l=>l.IsMotorway&&l.SpeedLimit==1.5),"recovered motorway speed cap");
                for(int i=1;i<lanes.Count;i++)Check(Point.Distance(lanes[i-1].Samples.Last(),lanes[i].Samples[0])<1e-8,"continuous motorway entry and exit");
                var snap=w.Observe();snap.Motorways[0].Start=new Cell(-1,-1);Check(w.Motorways[0].Start==start,"motorway snapshot detached");
                w.Step(220);Check(w.Cars.Any(c=>c.Moving&&c.Lanes.Any(l=>l.IsMotorway)),"dispatch uses motorway");
                int id=w.Motorways[0].Id;Check(w.RemoveMotorway(id),"retire motorway");
                Check(w.Motorways.Count==1&&w.Inventory[2]==0,"committed lanes retain inventory");
                Check(w.FindRoute(house.Access,shop.Access).Count==0,"new trips cannot use retired motorway");
                w.Step(3000);Check(w.TripsCompleted>0,"committed trip finishes");
                Check(w.Cars.All(c=>c.Stage==TripStage.Home),"committed cars return home");
                Check(w.Motorways.Count==0&&w.Inventory[2]==1,"stock released after clearing");
                var custom=new TrafficWorld(7,false,Rules.ForVersion(GameVersion.Custom));custom.Reset(7,ScenarioKind.EmptyLab);custom.Inventory[2]=10;
                Check(!custom.AddMotorway(start,end),"Custom still excludes motorways");
                Check(w.AddMotorway(start,end),"released motorway reusable");
                Check(w.Build(BuildTool.Remove,start)&&w.Motorways.Count==0&&w.Inventory[2]==1,"remove on empty endpoint removes motorway");
                w.Reset(7,ScenarioKind.EmptyLab);Check(w.Motorways.Count==0,"reset clears motorway state");
            });
            Test("motorway edits preserve traffic and cannot duplicate inventory",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                var w=new TrafficWorld(7,false,rules);w.Reset(7,ScenarioKind.EmptyLab);w.Inventory[2]=1;
                var house=w.SpawnBuilding(new Cell(5,5),0,true);var shop=w.SpawnBuilding(new Cell(30,4),0,false);
                Cell start=new Cell(6,5),end=new Cell(29,6),replacement=new Cell(28,6);
                Check(w.AddMotorway(start,end),"initial motorway");int id=w.Motorways[0].Id;
                w.Connect(house.Access,start);w.Connect(end,shop.Access);w.Step(220);
                Check(!w.EditMotorway(id,start,shop.Access),"invalid edit rejected atomically");
                Check(w.Inventory[2]==0&&w.Motorways.Count==1&&!w.Motorways[0].PendingRemoval,"failed edit leaves original intact");
                Check(w.EditMotorway(id,start,replacement),"edit reuses occupied motorway slot");
                Check(w.Inventory[2]==0&&w.Motorways.Count==2,"old committed geometry retained while new geometry is live");
                Check(w.Motorways.All(m=>m.Number==1),"replacement retains motorway number");
                Check(w.SpawnBuilding(replacement,1,true)==null,"building cannot overwrite an endpoint");
                w.Step(3000);Check(w.Cars.All(c=>c.Stage==TripStage.Home),"old outbound and return paths clear after edit");
                Check(w.Motorways.Count==1&&w.Inventory[2]==0,"old geometry release does not refund replacement slot");
                Check(w.RemoveMotorway(w.Motorways[0].Id)&&w.Inventory[2]==1,"final release returns one motorway only");
            });
            Test("original expansion reaches recovered final boundaries",()=>{
                foreach(var map in CityCatalog.Maps)
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.TickSeconds=20;rules.DemandCapacity=10000;
                    var w=new TrafficWorld(3,false,rules);w.Reset(3,map);double initial=w.CityZoom;
                    w.Step((int)Math.Ceiling(w.Map.Zoom[2]+w.Map.Zoom[3])+1);
                    Check(w.CityZoom==w.Map.Zoom[1]&&w.CityZoom>initial,"camera reaches final size for "+map);
                    var bounds=w.PlayableBounds;Check(bounds[0]>=0&&bounds[1]>=0&&bounds[2]<=50&&bounds[3]<=30,"full playable extent fits data canvas");
                }
                Check(CityCatalog.Get(ScenarioKind.Beijing).SpawnRamp[1]>CityCatalog.Get(ScenarioKind.LosAngeles).SpawnRamp[1],"city-specific ramps retained");
                Check(CityCatalog.Get(ScenarioKind.Tokyo).SpawnRamp[0]==45,"Tokyo later ramp retained");
            });
            Test("Original demand oscillation is shared by color group",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                var w=new TrafficWorld(9,false,rules);w.Reset(9,ScenarioKind.EmptyLab);
                var a=w.SpawnBuilding(new Cell(10,5),0,false);var b=w.SpawnBuilding(new Cell(20,5),0,false);var c=w.SpawnBuilding(new Cell(30,5),1,false);
                Check(w.OriginalDemandInterval(a)==w.OriginalDemandInterval(b),"same-color destinations share oscillation phase");
                Check(w.OriginalDemandInterval(a)!=w.OriginalDemandInterval(c),"different color profiles retain their demand");
                w.Step(59);Check(a.Demand==0&&b.Demand==0,"no demand before initial three-second delay");
                w.Step(2);Check(a.Demand==1&&b.Demand==1,"first pins after countdown");
            });
            Test("reference random generator matches installed-assembly oracle vectors",()=>{
                {var r=new ReferenceRandom(0UL);
                r=new ReferenceRandom(0UL);foreach(var expected in new int[]{-1246933298,-548476836,411637087,-958612273,285663429,1194354350,927646759,568977855,1922357842,556645914,-1673225430,-1564871940})Check(r.NextInt()==expected,"installed RNG seed 0 ints");
                r=new ReferenceRandom(0UL);foreach(var expected in new int[]{9,13,5,14,2,4,7,10,1,5,13,8})Check(r.Next(17)==expected,"installed RNG seed 0 bounded");
                r=new ReferenceRandom(0UL);foreach(var expected in new long[]{2493866597L,1096953673L,823274174L,1917224547L,571326858L,2388708700L,1855293518L,1137955710L,3844715684L,1113291828L,3346450861L,3129743881L})Check(r.NextFractionRaw()==expected,"installed RNG seed 0 fractionRaw");
                }
                {var r=new ReferenceRandom(1UL);
                r=new ReferenceRandom(1UL);foreach(var expected in new int[]{-1246933298,-1241242732,2010327980,-210880474,990052306,-938251308,-1567034028,-76974119,-1098817634,-1373536872,858282191,57193192})Check(r.NextInt()==expected,"installed RNG seed 1 ints");
                r=new ReferenceRandom(1UL);foreach(var expected in new int[]{9,12,1,5,16,11,14,12,11,8,12,7})Check(r.Next(17)==expected,"installed RNG seed 1 bounded");
                r=new ReferenceRandom(1UL);foreach(var expected in new long[]{2493866597L,2482485465L,4020655960L,421760949L,1980104612L,1876502617L,3134068057L,153948239L,2197635269L,2747073745L,1716564382L,114386384L})Check(r.NextFractionRaw()==expected,"installed RNG seed 1 fractionRaw");
                }
                {var r=new ReferenceRandom(42UL);
                r=new ReferenceRandom(42UL);foreach(var expected in new int[]{-1246933298,949144292,-1684880548,-1326492664,-775460045,1951613476,-744796364,-1383925913,1950021699,1780149742,1801282541,-274682106})Check(r.NextInt()==expected,"installed RNG seed 42 ints");
                r=new ReferenceRandom(42UL);foreach(var expected in new int[]{9,3,10,14,5,12,4,7,13,12,9,2})Check(r.Next(17)==expected,"installed RNG seed 42 bounded");
                r=new ReferenceRandom(42UL);foreach(var expected in new long[]{2493866597L,1898288584L,3369761097L,2652985329L,1550920091L,3903226952L,1489592729L,2767851827L,3900043398L,3560299484L,3602565082L,549364213L})Check(r.NextFractionRaw()==expected,"installed RNG seed 42 fractionRaw");
                }
                {var r=new ReferenceRandom(2147483647UL);
                r=new ReferenceRandom(2147483647UL);foreach(var expected in new int[]{-173191474,-903508028,2104944377,615753592,-2121503240,-1008753674,-396049748,115167655,-1054926094,-1310694431,-873000663,1766047313})Check(r.NextInt()==expected,"installed RNG seed 2147483647 ints");
                r=new ReferenceRandom(2147483647UL);foreach(var expected in new int[]{5,0,8,9,14,11,1,16,16,11,15,1})Check(r.Next(17)==expected,"installed RNG seed 2147483647 bounded");
                r=new ReferenceRandom(2147483647UL);foreach(var expected in new long[]{346382949L,1807016057L,4209888754L,1231507184L,4243006481L,2017507349L,792099497L,230335310L,2109852189L,2621388863L,1746001327L,3532094626L})Check(r.NextFractionRaw()==expected,"installed RNG seed 2147483647 fractionRaw");
                }
                {var r=new ReferenceRandom(4294967295UL);
                r=new ReferenceRandom(4294967295UL);foreach(var expected in new int[]{-1246933299,722805514,-2034888327,-870337569,1033376763,-1035512523,150665849,-1822718741,-274593548,-479776380,-1884192107,-1464033761})Check(r.NextInt()==expected,"installed RNG seed 4294967295 ints");
                r=new ReferenceRandom(4294967295UL);foreach(var expected in new int[]{8,7,12,8,7,12,0,10,7,1,4,1})Check(r.Next(17)==expected,"installed RNG seed 4294967295 bounded");
                r=new ReferenceRandom(4294967295UL);foreach(var expected in new long[]{2493866599L,1445611028L,4069776655L,1740675139L,2066753526L,2071025047L,301331698L,3645437483L,549187097L,959552761L,3768384215L,2928067523L})Check(r.NextFractionRaw()==expected,"installed RNG seed 4294967295 fractionRaw");
                }
            });
            Test("destination upgrades change demand and capacity without changing parking",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                var shop=w.SpawnBuilding(new Cell(15,5),0,false);double before=w.OriginalDemandInterval(shop);
                Check(shop.Parking.Length==3,"single Original lot has three bays");
                Check(w.ScheduleDestinationUpgrade(0),"schedule eligible destination");
                Check(!shop.Upgraded&&shop.UpgradeAt==10,"upgrade waits until minimum activation age");
                Check(!w.ScheduleDestinationUpgrade(0),"pending upgrade cannot be scheduled twice");
                w.Step(199);Check(!shop.Upgraded,"upgrade does not activate early");w.Step();
                Check(shop.Upgraded&&w.DestinationCapacity(shop)==9,"upgrade activates at ten seconds and raises capacity to nine");
                double after=w.OriginalDemandInterval(shop);shop.Upgraded=false;double atSameTime=w.OriginalDemandInterval(shop);shop.Upgraded=true;
                Check(Math.Abs(after*2-atSameTime)<1e-9,"upgraded demand is doubled at same oscillation phase");
                Check(shop.Width==2&&shop.Height==3&&shop.Parking.Length==3,"upgrade preserves existing lot and bays");
                var snapshot=w.Observe();Check(snapshot.Buildings[0].Upgraded&&snapshot.Buildings[0].DemandCapacity==9,"upgrade visible in observations");
                var custom=new TrafficWorld(42,false,Rules.ForVersion(GameVersion.Custom));custom.Reset(42,ScenarioKind.EmptyLab);
                var c=custom.SpawnBuilding(new Cell(15,5),0,false);Check(!custom.ScheduleDestinationUpgrade(0)&&!c.Upgraded&&c.Parking.Length==6,"Custom one-size behavior retained");
            });
            Test("all single-lot orientations have usable entrances and parking",()=>{
                for(int layout=0;layout<4;layout++)
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                    var house=w.SpawnBuilding(new Cell(5,5),0,true);var shop=w.SpawnBuilding(new Cell(15,4),0,false,0,layout);
                    Check(shop!=null&&shop.Width==(layout>=2?3:2)&&shop.Height==(layout>=2?2:3),"orientation footprint");
                    Check(w.BuildReferenceNetwork(),"roads reach oriented driveway");
                    for(int bay=0;bay<shop.Parking.Length;bay++)
                    {var point=w.ParkingPoint(shop,bay);Check(point.X>=shop.Cell.X&&point.X<shop.Cell.X+shop.Width&&point.Y>=shop.Cell.Y&&point.Y<shop.Cell.Y+shop.Height,"bay stays inside rotated lot");}
                    w.Step(4000);Check(w.TripsCompleted>0,"oriented parking completes visits: "+layout+" "+Summary(w));
                    Check(w.Cars.All(c=>!double.IsNaN(c.Position.X)&&!double.IsNaN(c.Position.Y)),"finite parking paths");
                }
            });
            Test("circle schedule events upgrade existing destinations",()=>{
                var map=CityCatalog.Get(ScenarioKind.LosAngeles);var plan=map.Plan;var circles=map.CircleZones;
                try
                {
                    map.Plan=new[]{new PlanChunk{Start=0,Duration=0,Ordered=true,Items=new[]{new double[]{0,0,0,1,1}}},new PlanChunk{Start=.5,Duration=0,Ordered=true,Items=new[]{new double[]{0,0,3,1,1}}}};
                    map.CircleZones=Enumerable.Range(0,map.BaseDemand.Length).Select(_=>Enumerable.Range(0,1500).ToArray()).ToArray();
                    var w=new TrafficWorld(42,false,Rules.ForVersion(GameVersion.OriginalReference));int shops=w.Buildings.Count(b=>!b.IsHouse);
                    Check(shops==1&&w.Observe().ScheduledSpawns.Single().Grouping==3,"upgrade event retained, not exported as normal shop");
                    w.Step(201);Check(w.Buildings.Count(b=>!b.IsHouse)==shops&&w.Buildings.Any(b=>b.Upgraded),"circle event upgrades in place");
                    Check(w.Observe().ScheduledSpawns.Length==0,"successful upgrade event consumed once");
                }
                finally{map.Plan=plan;map.CircleZones=circles;}
                Check(map.Plan.Any(ch=>ch.Items.Any(item=>item[2]==3)),"real LA plans retain circle events");
                Check(map.CircleZones.Any(zone=>zone.Length>0),"circle placement masks recovered from WeightTile data");
            });
            Test("shared destinations use one nine-bay car park in all orientations",()=>{
                for(int layout=0;layout<4;layout++)
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                    w.SpawnBuilding(new Cell(5,5),0,true);w.SpawnBuilding(new Cell(5,10),1,true);
                    var first=w.SpawnSharedCarpark(new Cell(15,5),0,layout);Check(first!=null,"shared footprint "+layout);
                    var second=w.JoinSharedCarpark(first.Id,1);Check(second!=null&&w.SameCarpark(first.Id,second.Id),"two colors share lot");
                    Check(ReferenceEquals(first.Parking,second.Parking)&&first.Parking.Length==9,"one occupancy array and nine bays");
                    Check(w.JoinSharedCarpark(first.Id,0)==null&&w.JoinSharedCarpark(first.Id,2)==null,"no duplicate color or third destination");
                    Check(first.Entrances.Length==2&&w.BuildReferenceNetwork(),"two entrances reachable");
                    foreach(var shop in new[]{first,second})for(int bay=0;bay<9;bay++)
                    {var p=w.ParkingPoint(shop,bay);Check(p.X>=shop.Cell.X&&p.X<shop.Cell.X+shop.Width&&p.Y>=shop.Cell.Y&&p.Y<shop.Cell.Y+shop.Height,"rotated shared bays remain inside lot");}
                    w.Step(5000);Check(w.TripsCompleted>2,"shared trips complete "+layout+" "+Summary(w));
                    Check(w.Cars.Where(c=>c.Stage!=TripStage.Home).All(c=>w.HasAccess(w.Buildings[c.ShopId],c.DestinationAccess)),"committed entrance retained");
                    var snapshot=w.Observe();snapshot.Buildings[first.Id].Parking[0]=999;snapshot.Buildings[first.Id].Entrances[0]=new Cell(-1,-1);
                    Check(first.Parking[0]!=999&&first.Entrances[0].X>=0,"shared snapshots detached");
                }
            });
            Test("London train stops generate station demand and crossing signals",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.DemandCapacity=10000;
                var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.London);rules.EnableCityGrowth=false;
                Check(w.RailLines.Count==1&&w.RailLines[0].Loop&&w.RailLines[0].Cells.Length==53&&w.Trains.Count==1,"recovered London rail and train origin");
                var station=w.Buildings.FirstOrDefault(b=>b.IsStation);Check(station!=null,"initial station placed");
                Check(station.Platform.Length==4&&station.Platform.All(c=>w.Rails[c.X,c.Y]),"platform follows four rail cells");
                station.Demand=0;w.Step(10);Check(station.Demand==0,"station has no ordinary timer demand");
                bool closed=false,reopened=false;Cell watched=new Cell(-1,-1);
                for(int i=0;i<2400;i++)
                {
                    w.Step();Check(w.Trains[0].Speed>=0&&w.Trains[0].Speed<=TrainTuning.Speed,"bounded train speed");
                    if(!closed){var cells=w.Observe().ClosedRailCrossings;if(cells.Length>0){watched=cells[0];closed=true;}}
                    else if(!w.IsRailCrossingClosed(watched))reopened=true;
                }
                Check(w.Trains[0].Stops>0&&station.Demand>0,"train stops and delivers passenger batch");
                Check(closed&&reopened,"crossings close and reopen after passage");
                var observation=w.Observe();observation.RailLines[0].Cells[0]=new Cell(-1,-1);Check(w.RailLines[0].Cells[0].X>=0,"rail snapshot detached");
                w.Reset(42,ScenarioKind.LosAngeles);Check(w.Trains.Count==0&&w.RailLines.Count==0&&w.Observe().ClosedRailCrossings.Length==0,"reset clears London rail state");
                var custom=new TrafficWorld(42,false,Rules.ForVersion(GameVersion.Custom));custom.Reset(42,ScenarioKind.London);
                Check(custom.Trains.Count==0&&custom.SpawnSharedCarpark(new Cell(15,5),0)==null,"Custom retains independent rules");
            });
            Test("vehicles wait at a closed railway crossing and resume after release",()=>{
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                var london=new TrafficWorld(42,false,rules);london.Reset(42,ScenarioKind.London);
                var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                var line=london.RailLines.Single();w.RailLines.Add(line);foreach(var c in line.Cells)w.Rails[c.X,c.Y]=true;
                var crossing=new Cell(12,11);int index=Array.IndexOf(line.Cells,crossing);Check(index>=0,"straight rail fixture");
                w.Trains.Add(new TrainState{Id=0,LineId=0,Distance=line.Offsets[index],Wait=1000});
                var house=w.SpawnBuilding(new Cell(8,11),0,true);var shop=w.SpawnBuilding(new Cell(16,9),0,false);
                Check(house!=null&&shop!=null&&w.DrawRoad(house.Access,shop.Access),"perpendicular crossing road");
                Check(!w.CanConnectAcrossRail(crossing,new Cell(12,12)),"roads cannot run along rails");
                shop.Demand=6;w.Step(800);
                Check(w.TripsCompleted==0&&w.Cars.Any(c=>c.Obstacle=="Train crossing"),"cars wait before active train crossing: "+Summary(w));
                w.Trains.Clear();w.Step(1600);Check(w.TripsCompleted>0&&!w.IsRailCrossingClosed(crossing),"cars resume after crossing releases: "+Summary(w));
            });
            Test("Original parking paths follow continuous circulation lanes and diagonal bays",()=>{
                foreach(bool shared in new[]{false,true})for(int layout=0;layout<4;layout++)
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);
                    var shop=shared?w.SpawnSharedCarpark(new Cell(15,5),0,layout):w.SpawnBuilding(new Cell(15,5),0,false,0,layout);
                    foreach(var access in shop.Entrances)for(int slot=0;slot<shop.Parking.Length;slot++)
                    {
                        var enter=w.ParkingRoute(shop,access,slot);var exit=w.ParkingRoute(shop,access,slot,true);
                        foreach(var route in new[]{enter,exit,w.ParkingDriveThrough(shop,access)})
                        {
                            for(int i=1;i<route.Count;i++)Check(Point.Distance(route[i-1].Samples.Last(),route[i].Samples[0])<1e-9,"internal parking lanes join continuously");
                            foreach(var point in route.SelectMany(l=>l.Samples))
                            {
                                Check(point.X>=shop.Cell.X&&point.X<=shop.Cell.X+shop.Width&&point.Y>=shop.Cell.Y&&point.Y<=shop.Cell.Y+shop.Height,"circulation remains in lot");
                                double across=layout<2?point.Y-shop.Cell.Y:point.X-shop.Cell.X;
                                bool high=layout<2?!(shared&&layout==1):shared&&layout==3;
                                Check(high?across>=2:across<=1,"cars stay in parking strip, outside destination footprints");
                            }
                        }
                        Check(Point.Distance(enter[0].Samples[0],w.ParkingAccessPoint(shop,access,true))<1e-9&&Point.Distance(exit.Last().Samples.Last(),w.ParkingAccessPoint(shop,access,false))<1e-9,"entrance and return continuity");
                        Check(Point.Distance(enter.Last().Samples.Last(),w.ParkingPoint(shop,slot))<1e-9&&Point.Distance(exit[0].Samples[0],w.ParkingPoint(shop,slot))<1e-9,"stop at bay midpoint");
                        Check(exit[0].ReleasesParking&&!exit.Skip(1).Any(l=>l.ReleasesParking),"release occurs when the bay clears");
                        Check(Point.Distance(enter.Last().Tangent(enter.Last().Length),w.ParkingHeading(shop,access))<1e-7,"parked heading follows diagonal bay");
                    }
                }
            });
            Test("full Original lots drive through before delivery and free bays before exiting",()=>{
                TrafficWorld fixture(){var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                    var world=new TrafficWorld(42,false,rules);world.Reset(42,ScenarioKind.EmptyLab);world.SpawnBuilding(new Cell(5,5),0,true);
                    var shop=world.SpawnBuilding(new Cell(15,4),0,false);shop.DemandCountdown=1e9;shop.Demand=1;world.BuildReferenceNetwork();return world;}
                var w=fixture();var lot=w.Buildings[1];for(int i=0;i<lot.Parking.Length;i++)lot.Parking[i]=999;
                Vehicle through=null;for(int i=0;i<4000&&through==null;i++){w.Step();through=w.Cars.FirstOrDefault(c=>c.DrivingThrough);}
                Check(through!=null&&through.Stage==TripStage.EnteringParking&&!through.HasDelivered&&w.TripsCompleted==0,"full-lot arrival does not deliver instantly at the entrance");
                Check(through.Lanes.Count>5&&through.ParkingSlot==-1,"drive-through uses internal circuit without reserving a bay");
                for(int i=0;i<4000&&!through.HasDelivered;i++)w.Step();
                Check(through.HasDelivered&&through.Stage==TripStage.EnteringParking&&through.Moving&&w.TripsCompleted==1,"one delivery when internal circulation is entered");
                for(int i=0;i<4000&&through.Stage==TripStage.EnteringParking;i++)w.Step();
                Check(through.Stage==TripStage.Returning&&w.TripsCompleted==1,"drive-through continues to the exit without double delivery");
                var normal=fixture();bool freed=false;
                for(int i=0;i<4000&&!freed;i++){normal.Step();freed=normal.Cars.Any(c=>c.Stage==TripStage.LeavingParking&&c.ParkingSlot==-1);}
                Check(freed,"bay becomes available before vehicle leaves the lot");
            });
            Test("arrival home or in a bay clears the current wait",()=>{
                // A queued car released within one creeping tick of its journey end arrives
                // below the 0.02 tiles/s waiting threshold. Its queue wait must not persist
                // while it is parked or at home, where it no longer receives movement updates.
                foreach(var stage in new[]{TripStage.Returning,TripStage.EnteringParking})
                {
                    var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.DemandCapacity=10000;
                    var w=new TrafficWorld(42,false,rules);w.Reset(42,ScenarioKind.EmptyLab);w.SpawnBuilding(new Cell(5,5),0,true);
                    var shop=w.SpawnBuilding(new Cell(15,4),0,false);shop.DemandCountdown=1e9;shop.Demand=1;w.BuildReferenceNetwork();
                    Vehicle car=null;
                    for(int i=0;i<8000&&car==null;i++){w.Step();car=w.Cars.FirstOrDefault(c=>c.Stage==stage&&c.Moving&&!c.DrivingThrough);}
                    Check(car!=null,"fixture reaches "+stage+": "+Summary(w));
                    car.RouteIndex=car.Lanes.Count-1;car.DistanceAlongLane=car.CurrentLane.Length-1e-4;car.Speed=0;car.Waiting=12;
                    double total=car.TotalWaiting;var arrived=stage==TripStage.Returning?TripStage.Home:TripStage.Parking;
                    for(int i=0;i<20&&car.Stage==stage;i++)w.Step();
                    Check(car.Stage==arrived,stage+" car arrives from its final creep: "+Summary(w));
                    Check(car.Waiting==0,arrived+" car keeps no stale queue wait: waiting="+car.Waiting);
                    Check(car.TotalWaiting>=total,"cumulative waiting is never reduced");
                }
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
