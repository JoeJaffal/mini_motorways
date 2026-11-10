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
                Require(Math.Abs(w.LaneSpeed(north,0,0)-.6)<1e-9&&w.RouteCost(new[]{north,new Cell(14,15)})==23,"route cost retains circulating speed advantage");checks++;
            }
            {
                var w=Lab();w.Step(2800);var choices=w.UpgradeChoices.Select(o=>(o.Type,o.Amount,o.Roads)).ToArray();
                w.Step(100);Require(choices.SequenceEqual(w.UpgradeChoices.Select(o=>(o.Type,o.Amount,o.Roads))),"pending choice remains stable");
                int stock=w.Inventory[0],grant=w.UpgradeChoices[0].Roads+(w.UpgradeChoices[0].Type==0?w.UpgradeChoices[0].Amount:0);
                Require(w.ChooseUpgrade(0)&&w.Inventory[0]==stock+grant&&!w.ChooseUpgrade(0),"reward grants concrete exactly once");checks++;
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
                        Require(!w.VehicleBodiesOverlap(moving[i].Position,moving[i].Heading,moving[j].Position,moving[j].Heading),"parking bodies remain separated");
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
