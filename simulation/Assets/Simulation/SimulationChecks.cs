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
                w.Step(79);Check(a.Demand==0&&b.Demand==0,"no demand before first-pin delay");
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
                        Check(Point.Distance(enter[0].Samples[0],new Point(access))<1e-9&&Point.Distance(exit.Last().Samples.Last(),new Point(access))<1e-9,"entrance and return continuity");
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
