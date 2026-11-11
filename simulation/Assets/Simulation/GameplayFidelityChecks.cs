using System;
using System.Linq;
using System.Collections.Generic;
namespace MotorwaysSim
{
    public static class GameplayFidelityChecks
    {
        static void Require(bool value,string message){if(!value)throw new InvalidOperationException("FIDELITY CHECK FAILED: "+message);}
        static TrafficWorld Lab()
        {
            var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
            var world=new TrafficWorld(40,false,rules);world.Reset(40,ScenarioKind.EmptyLab);return world;
        }
        public static int Run()
        {
            int checks=0;
            {
                var w=Lab();var home=w.SpawnBuilding(new Cell(5,7),0,true);
                var shop=w.SpawnBuilding(new Cell(12,5),0,false);
                Require(w.DrawRoad(home.Access,shop.Access)&&w.Inventory[0]==20,"five ordinary edges, free building connections");
                w.DrawRoad(home.Access,shop.Access);Require(w.Inventory[0]==20,"redraw spends nothing");
                w.DrawRoad(new Cell(8,7),new Cell(8,9));Require(w.Inventory[0]==18,"two-edge branch priced independently");
                w.Build(BuildTool.Remove,new Cell(8,8));Require(w.Inventory[0]==20,"both deleted branch edges refunded");
                for(int x=6;x<12;x++)w.Build(BuildTool.Remove,new Cell(x,7));
                Require(w.Inventory[0]==25,"all original concrete restored");checks++;
            }
            {
                var w=Lab();w.Inventory[0]=1;w.DrawRoad(new Cell(5,5),new Cell(9,5));
                Require(w.Inventory[0]==0&&w.IsRoad(new Cell(6,5))&&!w.IsRoad(new Cell(7,5)),"stroke stops at last affordable connection");
                var home=w.SpawnBuilding(new Cell(4,5),0,true);
                Require(home!=null&&w.Connect(home.Access,new Cell(5,5)),"building connection remains free at zero roads");checks++;
            }
            {
                var w=Lab();var home=w.SpawnBuilding(new Cell(5,5),0,true);
                var shop=w.SpawnBuilding(new Cell(10,3),0,false);
                Require(!w.HasSufficientHouseSupply(shop),"one house insufficient for base demand");
                w.SpawnBuilding(new Cell(6,6),0,true);
                Require(w.HasSufficientHouseSupply(shop),"two near houses supply base demand");
                shop.Upgraded=true;Require(!w.HasSufficientHouseSupply(shop),"upgrade triggers extra supply requirement");
                Require(Math.Abs(w.HouseSupplyContribution(home,shop)-.875)<1e-9,"installed near-house contribution");
                Require(ReferenceCurves.Evaluate(OriginalGameplayTuning.HouseContribution,7)==OriginalGameplayTuning.HouseContribution[1][1],"step curve takes exact new key");checks++;
            }
            {
                var w=Lab();w.Step(40);var shop=w.SpawnBuilding(new Cell(10,5),0,false);
                Require(shop.DemandCountdown==4,"later destination starts the original's four-second first-pin timer (DestinationModel.Initialize)");
                w.Step(78);Require(shop.Demand==0,"no pin before four seconds");w.Step(3);Require(shop.Demand==1,"first pin at four seconds");checks++;
            }
            {
                var w=Lab();w.DrawRoad(new Cell(5,5),new Cell(9,5));
                var home=w.SpawnBuilding(new Cell(5,9),0,true);var car=w.Cars.First();
                car.Stage=TripStage.Returning;car.RouteVersion=w.NetworkVersion;
                car.Lanes=w.MakeLanes(new[]{new Cell(8,5),new Cell(9,5)});
                car.ReturnRoute=new List<Cell>{new Cell(5,5),new Cell(6,5),new Cell(7,5),new Cell(8,5),new Cell(9,5)};
                int stock=w.Inventory[0];w.Build(BuildTool.Remove,new Cell(6,5));
                Require(w.Tile(new Cell(6,5))==Infrastructure.None&&w.Inventory[0]==stock+2,"already-passed return road releases before car reaches home");checks++;
            }
            {
                var w=Lab();var shop=w.SpawnSharedCarpark(new Cell(12,10),0);
                var a=w.SpawnBuilding(new Cell(5,5),0,true);var b=w.SpawnBuilding(new Cell(5,7),0,true);
                var cars=w.Cars.Where(c=>c.HomeId==a.Id||c.HomeId==b.Id).Take(2).ToArray();
                for(int i=0;i<2;i++)
                {
                    int slot=i*8;var car=cars[i];car.ShopId=shop.Id;car.Stage=TripStage.Parking;car.ParkingSlot=slot;shop.Parking[slot]=car.Id;
                    car.ParkedPosition=w.ParkingPoint(shop,slot);car.DestinationAccess=shop.Access;car.Dwell=-1;
                }
                w.Step(1);
                Require(cars.All(c=>c.Stage==TripStage.LeavingParking),"independent parked cars may depart concurrently");
                Require(cars.All(c=>c.CurrentLane.IsParking&&c.CurrentLane.CarparkId==shop.CarparkId),"departures use identified physical lot lanes");checks++;
            }
            {
                var w=Lab();w.Inventory[4]=1;var center=new Cell(15,15);w.Build(BuildTool.Roundabout,center);
                var north=new Cell(15,14);
                Require(!w.RoundaboutAllowsConnection(north,center),"no entry through roundabout center");
                foreach(var offset in new[]{new Cell(-1,-1),new Cell(0,-1),new Cell(1,-1),new Cell(-1,0),new Cell(1,0)})
                    Require(w.RoundaboutAllowsConnection(north,north+offset),"original five outward exit directions");
                Require(Math.Abs(w.LaneSpeed(north,TrafficWorld.Direction(new Cell(16,15),north),TrafficWorld.Direction(north,new Cell(14,15)))-.6)<1e-9&&w.RouteCost(new[]{north,new Cell(14,15)})==23,"route cost retains circulating speed advantage");checks++;
            }
            {
                var w=Lab();w.Step(2800);var choices=w.UpgradeChoices.Select(o=>(o.Type,o.Amount,o.Roads)).ToArray();
                w.Step(100);Require(choices.SequenceEqual(w.UpgradeChoices.Select(o=>(o.Type,o.Amount,o.Roads))),"pending choice remains stable");
                int stock=w.Inventory[0],grant=w.UpgradeChoices[0].Roads+(w.UpgradeChoices[0].Type==0?w.UpgradeChoices[0].Amount:0);
                Require(w.ChooseUpgrade(0)&&w.Inventory[0]==stock+grant&&!w.ChooseUpgrade(0),"reward grants concrete exactly once");checks++;
            }
            {
                // Original TileEditor: a stroke into a house from another side turns its driveway toward that road.
                var w=Lab();w.Inventory[0]=1000;var home=w.SpawnBuilding(new Cell(10,10),0,true,0);
                int before=home.DrivewayDirection;var south=new Cell(10,13);
                Require(w.DrawRoad(south,home.Cell),"stroke into a house");
                Require(home.DrivewayDirection==TrafficWorld.Direction(home.Cell,new Cell(10,11))&&w.Degree(new Cell(10,11))>0,"driveway turned toward the arriving road (was "+before+")");
                checks++;
            }
            {
                // Original tile corners: a diagonal step runs tile lane (ends 0.5 from centre), corner lane (~0.41), tile lane.
                var w=Lab();w.Inventory[0]=1000;Require(w.DrawRoad(new Cell(10,10),new Cell(13,13)),"diagonal road drawn");
                var lanes=w.MakeLanes(new[]{new Cell(10,10),new Cell(11,11),new Cell(12,12),new Cell(13,13)});
                Require(lanes.Count==7&&lanes[1].IsCorner&&lanes[3].IsCorner&&lanes[5].IsCorner&&!lanes[2].IsCorner,"tile and corner lanes alternate on a diagonal");
                Require(Math.Abs(lanes[1].Length-(Math.Sqrt(2)-1))<1e-6,"corner lane spans the corner region (sqrt2 - 1 tiles)");
                for(int i=1;i<lanes.Count;i++)Require(Point.Distance(lanes[i-1].Samples.Last(),lanes[i].Samples[0])<1e-9,"diagonal lanes are continuous");
                checks++;
            }
            {
                // Original corner chunk with four nodes: crossing diagonals form a junction where cars cross and turn.
                var w=Lab();w.Inventory[0]=1000;
                Cell a=new Cell(10,10),b=new Cell(11,11),c=new Cell(11,10),d=new Cell(10,11);
                Require(w.DrawRoad(new Cell(8,8),new Cell(13,13)),"first diagonal");
                Require(w.DrawRoad(new Cell(13,8),new Cell(8,13))&&w.Degree(c)==2&&w.Degree(d)==2,"crossing diagonal accepted on land");
                Require(w.FindRoute(a,b).Count==2,"straight through the crossing corner");
                var turn=w.FindRoute(a,c);Require(turn.Count==2&&turn[1]==c,"turn at the crossing corner onto the other diagonal");
                var lanes=w.MakeLanes(new[]{new Cell(9,9),a,c,new Cell(12,9)});
                Require(lanes.Count(l=>l.IsCorner)==3&&lanes.Any(l=>l.Key.StartsWith("cornerturn:")&&l.IsJunction),"turn runs through a turning corner lane");
                for(int i=1;i<lanes.Count;i++)Require(Point.Distance(lanes[i-1].Samples.Last(),lanes[i].Samples[0])<1e-9,"turn lanes are continuous");
                var se=w.MakeLanes(new[]{a,b})[1];var sw=w.MakeLanes(new[]{c,d})[1];var nw=w.MakeLanes(new[]{b,a})[1];
                Require(se.IsCorner&&sw.IsCorner&&se.ChunkCell==sw.ChunkCell&&se.ChunkCell.X<0&&se.IsJunction,"both diagonals share one corner chunk");
                Require(w.ConflictsPublic(se,sw)&&!w.ConflictsPublic(se,nw),"crossing lanes conflict, opposite lanes do not");
                var x=Lab();x.Inventory[0]=1000;x.Inventory[1]=5;var water=new Cell(21,10);x.Water[water.X,water.Y]=true;
                Require(x.DrawRoad(new Cell(23,10),water)&&x.Degree(water)==1,"bridge onto the water tile");
                Require(x.DrawRoad(new Cell(20,10),new Cell(21,11))&&x.Build(BuildTool.Road,new Cell(20,11)),"land diagonal beside it");
                Require(!x.Connect(water,new Cell(20,11))&&x.LastAction.Contains("Crossing diagonal"),"no crossing diagonal from a water tile");
                // Traffic on both diagonals and a turn: everything is delivered and crossing lanes are never occupied together.
                var f=Lab();f.Inventory[0]=1000;f.Rules.OvercrowdingSeconds=100000;
                var h0=f.SpawnBuilding(new Cell(6,6),0,true);var s0=f.SpawnBuilding(new Cell(16,16),0,false);
                var h1=f.SpawnBuilding(new Cell(16,5),1,true);var s1=f.SpawnBuilding(new Cell(4,16),1,false);
                Cell front0=s0.Access+TrafficWorld.Directions[s0.DrivewayDirection],front1=s1.Access+TrafficWorld.Directions[s1.DrivewayDirection];
                Require(f.DrawRoad(h0.Access,new Cell(8,8))&&f.DrawRoad(new Cell(8,8),new Cell(13,13))&&f.DrawRoad(new Cell(13,13),front0)&&f.DrawRoad(front0,s0.Access),"first crossing route");
                Require(f.DrawRoad(h1.Access,new Cell(13,8))&&f.DrawRoad(new Cell(13,8),new Cell(8,13))&&f.DrawRoad(new Cell(8,13),new Cell(3,13))&&f.DrawRoad(new Cell(3,13),front1)&&f.DrawRoad(front1,s1.Access),"second crossing route");
                Require(f.FindRoute(h0.Access,s0.Access).Contains(a)&&f.FindRoute(h1.Access,s1.Access).Contains(c)&&f.FindRoute(h0.Access,s1.Access).Contains(d),"routes use the crossing, one with a turn");
                s0.Demand=6;s0.DemandCountdown=1e9;s1.Demand=6;s1.DemandCountdown=1e9;
                for(int tick=0;tick<8000&&!(f.TripsCompleted==12&&f.ActiveCars==0);tick++)
                {
                    f.Step();var inCorner=f.Cars.Where(car=>car.Moving&&car.CurrentLane.IsJunction&&car.CurrentLane.IsCorner).ToArray();
                    for(int i=0;i<inCorner.Length;i++)for(int j=i+1;j<inCorner.Length;j++)
                        Require(!f.ConflictsPublic(inCorner[i].CurrentLane,inCorner[j].CurrentLane),"crossing lanes are never occupied together");
                }
                Require(f.TripsCompleted==12&&f.ActiveCars==0,"all twelve trips through the crossing are delivered");
                checks++;
            }
            foreach(bool shared in new[]{false,true})
            {
                var w=Lab();w.Inventory[0]=1000;w.Rules.OvercrowdingSeconds=100000;
                var shop=shared?w.SpawnSharedCarpark(new Cell(20,10),0):w.SpawnBuilding(new Cell(20,10),0,false);
                foreach(var cell in new[]{new Cell(5,12),new Cell(5,15),new Cell(5,18),new Cell(5,21)})
                {
                    var home=w.SpawnBuilding(cell,0,true);w.DrawRoad(home.Access,new Cell(10,cell.Y));
                    w.DrawRoad(new Cell(10,cell.Y),new Cell(10,12));
                }
                w.DrawRoad(new Cell(10,12),shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;
                int concurrent=0;
                for(int tick=0;tick<6000;tick++)
                {
                    w.Step();var moving=w.Cars.Where(c=>c.Moving&&c.CurrentLane.IsParking).ToArray();
                    concurrent=Math.Max(concurrent,moving.Length);
                    for(int i=0;i<moving.Length;i++)for(int j=i+1;j<moving.Length;j++)
                        Require(Point.Distance(moving[i].Position,moving[j].Position)>=.15,"parking cars never share a position (the original has no body-clearance check; chunk arbitration and following keep cars apart)");
                    if(w.TripsCompleted==8&&w.ActiveCars==0)break;
                }
                Require(w.TripsCompleted==8&&w.ActiveCars==0&&concurrent>=2,"eight-car parking queue clears with safe concurrency: shared="+shared);
                checks++;
            }
            {
                var w=Lab();w.Inventory[0]=1000;
                var home=w.SpawnBuilding(new Cell(5,10),0,true);var shop=w.SpawnBuilding(new Cell(40,8),0,false);
                w.DrawRoad(home.Access,shop.Access);shop.Demand=1;shop.DemandCountdown=1e9;
                double fastest=0;for(int tick=0;tick<1600;tick++){w.Step();fastest=Math.Max(fastest,w.Cars.Max(c=>c.Speed));}
                Require(fastest>1.4&&fastest<1.50001,"Original free-flow movement reaches reference3-world-unit target, converted to tiles");
                Require(w.TripsCompleted==1,"long straight ordinary-road fixture delivers exactly its one demand");checks++;
            }
            {
                var w=Lab();var home=w.SpawnBuilding(new Cell(5,5),0,true);var car=w.Cars.First();
                car.Lanes=new List<Lane>{new Lane{Length=1,SpeedLimit=1},new Lane{Length=1,SpeedLimit=1},new Lane{Length=3,SpeedLimit=.5}};
                car.RouteIndex=0;car.DistanceAlongLane=.5;
                Require(Math.Abs(w.DesiredMovementSpeed(car)-2.4)<1e-9,"ordinary lookahead: half unit at1, unit at1, unit at.5, then reference movement factor");
                car.Lanes[0].IsMotorway=true;
                Require(Math.Abs(w.DesiredMovementSpeed(car)-1.5)<1e-9,"motorway lookahead uses minimum rather than ordinary weighted average");checks++;
            }
            return checks;
        }
    }
}
