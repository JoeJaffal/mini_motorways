using System;
using System.Linq;
namespace MotorwaysSim
{
    public static class ParkingFlowChecks
    {
        public static int Run()
        {
            int checks=0;
            foreach(int seed in new[]{40,42})foreach(int layout in new[]{0,1,2,3})
            {
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.OvercrowdingSeconds=100000;
                var w=new TrafficWorld(seed,false,rules);w.Reset(seed,ScenarioKind.EmptyLab);w.Inventory[0]=1000;
                var shop=w.SpawnBuilding(new Cell(20,10),0,false,0,layout);
                var hub=layout==0?new Cell(10,12):layout==1?new Cell(30,12):layout==2?new Cell(20,6):new Cell(20,18);
                for(int i=0;i<4;i++)
                {
                    var cell=layout==0?new Cell(5,12+i*3):layout==1?new Cell(35,12+i*3):layout==2?new Cell(20+i*3,3):new Cell(20+i*3,23);
                    var home=w.SpawnBuilding(cell,0,true);var bend=layout<2?new Cell(hub.X,cell.Y):new Cell(cell.X,hub.Y);
                    w.DrawRoad(home.Access,bend);w.DrawRoad(bend,hub);
                }
                w.DrawRoad(hub,shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;
                int concurrent=0;
                for(int tick=0;tick<6000;tick++)
                {
                    w.Step();var cars=w.Cars.Where(c=>c.Stage!=TripStage.Home&&Point.Distance(c.Position,new Point(shop.Access))<4).ToArray();
                    concurrent=Math.Max(concurrent,cars.Count(c=>c.Moving&&c.CurrentLane.IsParking));
                    for(int i=0;i<cars.Length;i++)for(int j=i+1;j<cars.Length;j++)
                        if(w.VehicleBodiesOverlap(cars[i].Position,cars[i].Heading,cars[j].Position,cars[j].Heading))
                            throw new InvalidOperationException("PARKING FLOW: body overlap seed="+seed+" layout="+layout+" time="+w.Time+" cars="+cars[i].Id+","+cars[j].Id);
                    if(w.TripsCompleted==8&&w.ActiveCars==0)break;
                }
                if(w.TripsCompleted!=8||w.ActiveCars!=0||concurrent<2)
                    throw new InvalidOperationException("PARKING FLOW: uncleared queue seed="+seed+" layout="+layout+" trips="+w.TripsCompleted+" active="+w.ActiveCars+" "+string.Join(";",w.Cars.Select(c=>c.Id+" "+c.Stage+" "+c.Obstacle+" "+c.Waiting)));
                checks++;
            }
            return checks;
        }
    }
}
