using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        Building SharedTransitBetween(Cell from,Cell to)
        {
            var lot=AccessBuildingAt(from);
            return Rules.Version==GameVersion.OriginalReference&&lot!=null&&!lot.IsHouse&&lot.SharedLot&&from!=to&&
                HasAccess(lot,from)&&HasAccess(lot,to)?lot:null;
        }
        public List<Lane> ParkingTransitRoute(Building lot,Cell from,Cell to)
        {
            if(SharedTransitBetween(from,to)==null)throw new ArgumentException("Transit needs two entrances of the same shared carpark");
            bool forward=AccessDirection(lot,from)==4||AccessDirection(lot,from)==6;
            var lanes=new List<Lane>{ParkingConnector(lot,from,true)};
            if(forward)for(int i=0;i<lot.Parking.Length;i++)lanes.Add(ParkingThroughBay(lot,i,true));
            else for(int i=lot.Parking.Length-1;i>=0;i--)lanes.Add(ParkingThroughBay(lot,i,false));
            lanes.Add(ParkingConnector(lot,to,false));return lanes;
        }
        double SharedTransitCost(Building lot,Cell from,Cell to)=>ParkingTransitRoute(lot,from,to)
            .Sum(l=>Math.Max(1,Math.Floor(20*l.Length/Math.Max(.01,l.SpeedLimit))));
        int PhysicalCarpark(Vehicle car)
        {
            if(car.Stage==TripStage.Parking&&car.ShopId>=0)return Buildings[car.ShopId].CarparkId;
            if(!car.Moving)return -1;
            if(car.CurrentLane.IsParking)return car.CurrentLane.CarparkId;
            if(car.ShopId>=0&&(HasAccess(Buildings[car.ShopId],car.CurrentLane.Tile)||HasAccess(Buildings[car.ShopId],car.CurrentLane.Next)))
                return Buildings[car.ShopId].CarparkId;
            double distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count&&distance<Rules.CarLength+.5;i++)
            {if(car.Lanes[i].IsParking)return car.Lanes[i].CarparkId;distance+=car.Lanes[i].Length;}
            if(car.RouteIndex>0&&car.Lanes[car.RouteIndex-1].IsParking&&car.DistanceAlongLane<Rules.CarLength+.2)
                return car.Lanes[car.RouteIndex-1].CarparkId;
            return -1;
        }
        bool SamePhysicalCarpark(Vehicle a,Vehicle b){int lot=PhysicalCarpark(a);return lot>=0&&lot==PhysicalCarpark(b);}
    }
}
