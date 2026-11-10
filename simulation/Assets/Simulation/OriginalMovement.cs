using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference lane speeds and movement details recovered from the original (decision 081):
    // GameBehaviourModel.GetLaneSpeed and VehicleMovementProcess (maximum acceleration choice, intersection
    // approach slowdown, junction stopping offset, controlled-chunk boost).
    public sealed partial class TrafficWorld
    {
        // Original GetLaneSpeed for one tile lane (prev -> at -> next). Ring lanes (both ends on the ring) use the
        // roundabout multiplier and no turn factor; pathfinding charges them at default speed. Entry and exit lanes
        // of a roundabout tile use default speed with the turn factor. A lane coming off a motorway has no turn
        // factor. The intersection factor 0.5 applies to the lane whose next tile offers more than one way on
        // (the approach lane), unless that tile is signal-controlled or part of a roundabout, or the lane is a
        // U-turn or roundabout lane.
        double OriginalLaneSpeed(Cell at,int incoming,int outgoing,bool fromMotorway,bool forCost)
        {
            double speed=Rules.CarSpeed;var round=RoundaboutAt(at);
            Cell next=at+Directions[outgoing];
            if(round!=null&&round.Ring.Contains(next))
            {
                // Pathfinding: the original charges its ring arc (~1.16 tiles per quarter) at default speed; our
                // centre-to-centre step (1.41 tiles) at the ring speed gives the same cost (23), so keep the ring speed.
                if(incoming>=8||round.Ring.Contains(new Cell(at.X-Directions[incoming].X,at.Y-Directions[incoming].Y)))return speed*Rules.RoundaboutMultiplier;
            }
            bool uTurn=false;
            if(incoming<8&&!fromMotorway)
            {
                int turn=Math.Abs(incoming-outgoing);turn=Math.Min(turn,8-turn);uTurn=turn==4;
                if(turn==2)speed*=Rules.RightAngleMultiplier;else if(turn>=3)speed*=Rules.SharpTurnMultiplier;
            }
            if(incoming<8&&!uTurn&&round==null&&InBounds(next)&&Degree(next)>=3&&Tile(next)!=Infrastructure.TrafficLight&&RoundaboutAt(next)==null)
                speed*=Rules.IntersectionMultiplier;
            return speed;
        }

        // Original NumberOfRoadsAtIntersectionToSlowDownFor: distinct roads at the chunk, ignoring house driveways,
        // carpark entrances and roundabout lanes (IgnoreHouses/IgnoreDestinationsForIntersectionSlowDown = 1).
        int RoadsForIntersectionSlowdown(Cell tile)
        {
            if(!InBounds(tile)||RoundaboutAt(tile)!=null)return 0;
            int mask=Connections[tile.X,tile.Y],count=0;
            for(int d=0;d<8;d++)
            {
                if((mask&(1<<d))==0)continue;var other=tile+Directions[d];
                if(AccessBuildingAt(other)!=null||RoundaboutAt(other)!=null)continue;
                count++;
            }
            return count;
        }

        bool IsControlledLane(Lane lane)=>lane!=null&&!lane.IsParking&&!lane.IsMotorway&&Signals.ContainsKey(lane.Tile);

        // Original maximum acceleration: roundabout if the current or next chunk is a roundabout; controlled if the
        // current or next chunk is signal-controlled or the car's own driveway, or near the end of a motorway lane.
        double OriginalMaximumAcceleration(Vehicle car,Lane current,double distanceAlong)
        {
            var next=car.RouteIndex+1<car.Lanes.Count?car.Lanes[car.RouteIndex+1]:null;
            if(current.IsRoundabout||next!=null&&next.IsRoundabout)return Rules.RoundaboutAcceleration;
            var home=car.HomeId>=0&&car.HomeId<Buildings.Count?Buildings[car.HomeId].Cell:new Cell(-1,-1);
            bool driveway=!current.IsParking&&current.Tile==home||next!=null&&!next.IsParking&&next.Tile==home;
            bool motorwayEnd=current.IsMotorway&&current.Length-distanceAlong<Rules.CarLength;
            return driveway||IsControlledLane(current)||IsControlledLane(next)||motorwayEnd?Rules.ControlledAcceleration:Rules.MaxAcceleration;
        }
    }
}
