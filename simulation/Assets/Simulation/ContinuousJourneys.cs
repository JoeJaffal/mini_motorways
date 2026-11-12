using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference trips are one continuous path, as in the original (decision 079). The original's outbound
    // path ends on the carpark entrance lane; when the car moves onto the lane just before it, ParkVehiclesProcess
    // picks a free bay (or a drive-through) and appends the in-lot lanes. A car leaving its bay gets one path from
    // the bay to its house. So a car never brakes to a stop at a leg boundary, and its lookahead sees the cars in
    // the lot ahead. Stage changes happen at recorded lane indices instead of at leg ends.
    public sealed partial class TrafficWorld
    {
        bool ContinuousJourneys=>Rules.Version==GameVersion.OriginalReference;

        // Outbound path: end with the destination's entrance lane (not yet the in-lot lanes).
        void AppendEntranceLane(Vehicle car)
        {
            if(!ContinuousJourneys||car.Stage!=TripStage.Outbound||car.ShopId<0||car.Lanes.Count==0)return;
            var shop=Buildings[car.ShopId];if(shop.Parking==null||!HasAccess(shop,car.DestinationAccess))return;
            car.ParkingLegAt=car.Lanes.Count;car.ParkingLegAttached=false;car.Lanes.Add(ParkingConnector(shop,car.DestinationAccess,true));
        }

        void AppendReturnLanes(Vehicle car)
        {
            if(!ContinuousJourneys)return;
            if(OriginalRepath||car.ReturnRoute.Any(InPlannedRoundabout))
            {var back=FindRoute(car.DestinationAccess,Buildings[car.HomeId].Access,true);if(back.Count>1)car.ReturnRoute=back;}
            if(car.ReturnRoute.Count<2)return;
            int at=car.Lanes.Count;car.Lanes.AddRange(MakeLanes(car.ReturnRoute));car.LegMarks.Add((at,TripStage.Returning));car.RouteVersion=NetworkVersion;
        }

        void AttachParkingLeg(Vehicle car)
        {
            var shop=Buildings[car.ShopId];int at=car.ParkingLegAt;car.ParkingLegAttached=true;
            var free=Enumerable.Range(0,shop.Parking.Length).Where(i=>shop.Parking[i]<0).ToList();
            car.LegMarks.Add((at,TripStage.EnteringParking));
            if(free.Count==0)
            {
                car.DrivingThrough=true;car.Lanes[at].DeliversDriveThrough=true;
                car.Lanes.AddRange(ParkingDriveThrough(shop,car.DestinationAccess).Skip(1));AppendReturnLanes(car);
            }
            else
            {
                int slot=free.Count==1?free[0]:free[random.Next(free.Count)];
                car.ParkingSlot=slot;shop.Parking[slot]=car.Id;
                car.Lanes.AddRange(ParkingRoute(shop,car.DestinationAccess,slot).Skip(1));
            }
            RegisterRoute(car,true);
        }

        // Called whenever a car's lane index or path changes.
        void UpdateLegs(Vehicle car)
        {
            if(!ContinuousJourneys||!car.Moving)return;
            if(car.Stage==TripStage.Outbound&&car.ParkingLegAt>=0&&!car.ParkingLegAttached&&car.RouteIndex>=car.ParkingLegAt-1)AttachParkingLeg(car);
            while(car.LegMarks.Count>0&&car.RouteIndex>=car.LegMarks[0].Index)
            {
                var stage=car.LegMarks[0].Stage;car.LegMarks.RemoveAt(0);
                if(stage==TripStage.EnteringParking){car.Stage=TripStage.EnteringParking;car.At=car.DestinationAccess;car.Next=car.DestinationAccess;}
                else if(stage==TripStage.Returning)
                {
                    ReleaseParkingSlot(car);car.Stage=TripStage.Returning;car.Route=new List<Cell>(car.ReturnRoute);car.SegmentEntered=Time;
                }
            }
            // Original AcceptVehicleArrival: the pin clears, the score counts and the 3 s parking timer starts when the
            // car enters its bay lane, not when it reaches the bay's middle.
            if(car.Stage==TripStage.EnteringParking&&!car.DrivingThrough&&!car.HasDelivered&&car.CurrentLane.Key.Contains(":bay-park:"))
            {Deliver(car);car.Dwell=Rules.ServiceSeconds;}
            // Original: a returning car is waiting for a destination (dispatchable) as soon as it enters its driveway lane.
            if(car.Stage==TripStage.Returning&&car.RouteIndex==car.Lanes.Count-1&&car.HomeId>=0&&car.CurrentLane.Tile==Buildings[car.HomeId].Cell)
                FinishHome(car);
        }
    }
}
