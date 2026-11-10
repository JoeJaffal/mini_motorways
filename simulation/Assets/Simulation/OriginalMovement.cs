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

        // Original RoadTileConnection.IntersectsOtherConnection (right-hand traffic, smallIntersection = true), decided
        // from the sides a lane enters and leaves its tile: same exit conflicts (unless crossing in front of a stopped
        // car is allowed and the entries differ), same entry never conflicts, exact reversal never conflicts, a lane
        // conflicts with the other's half-turn rotation, otherwise the lanes cross when exactly one of the other's
        // sides lies clockwise from this lane's entry through its exit. Our direction indices are clockwise like the
        // original's, so the cyclic test needs no remapping.
        static bool ConnectionsIntersect(Lane a,Lane b,bool allowCrossingInFrontOfOther)
        {
            int ai=(a.Incoming+4)%8,ao=a.Outgoing,bi=(b.Incoming+4)%8,bo=b.Outgoing;
            if(ao==bo&&(!allowCrossingInFrontOfOther||ai==bi))return true;
            if(ai==bi)return false;
            if(ai==bo&&ao==bi)return false;
            if(!b.IsMotorway&&ai==(bi+4)%8&&ao==(bo+4)%8)return true;
            if(allowCrossingInFrontOfOther)return false;
            int count=0;
            for(int d=ai;d!=(ao+1)%8;d=(d+1)%8)if(bi==d||bo==d)count++;
            return count==1;
        }

        // Original motorway lanes (LaneUpdateProcess, AddMotorwayAction.ValidTileDirectionFor): each end tile has a
        // slot in the direction closest to the other end; the start tile keeps an ordinary lane from its entry edge to
        // that slot (arbitrated with the tile's other lanes, turn factor only, since its single outbound lane is the
        // motorway); a straight bespoke motorway lane joins the two slot edges at motorway speed. We take the closest
        // direction and do not model the original's fallback to a neighbouring free slot.
        static int ClosestDirection(Cell from,Cell to)
        {
            double dx=to.X-from.X,dy=to.Y-from.Y,best=double.NegativeInfinity;int result=0;
            for(int d=0;d<8;d++){var v=DirectionVector(d);double dot=v.X*dx+v.Y*dy;if(dot>best+1e-9){best=dot;result=d;}}
            return result;
        }
        static Point DirectionVector(int d)=>new Point(Directions[d].X,Directions[d].Y).Unit;
        static Point SlotPoint(Cell tile,int d)=>new Point(tile)+new Point(Directions[d].X*.5,Directions[d].Y*.5);

        List<Lane> OriginalMotorwayStart(MotorwayState motorway,Cell at,Cell prev,Cell next,Point start,Point incoming,int inDir)
        {
            int slot=ClosestDirection(at,next),endSlot=ClosestDirection(next,at);
            var out1=DirectionVector(slot);var slotEnd=SlotPoint(at,slot)+out1.Right*Rules.LaneOffset;
            double length=Point.Distance(start,slotEnd);
            var local=CreateLane(Cubic(start,start+incoming*Math.Min(.35,length*.45),slotEnd-out1*Math.Min(.35,length*.45),slotEnd,12),at,prev,next,inDir,slot);
            double speed=Rules.CarSpeed;
            if(inDir<8){int turn=Math.Abs(inDir-slot);turn=Math.Min(turn,8-turn);if(turn==2)speed*=Rules.RightAngleMultiplier;else if(turn>=3)speed*=Rules.SharpTurnMultiplier;}
            local.SpeedLimit=speed;local.IsJunction=Degree(at)>=3||Tile(at)==Infrastructure.TrafficLight;
            var travel=DirectionVector((endSlot+4)%8);var entry=SlotPoint(next,endSlot)+travel.Right*Rules.LaneOffset;
            var points=new Point[9];for(int k=0;k<9;k++)points[k]=slotEnd+(entry-slotEnd)*(k/8.0);
            var fast=CreateLane(points,at,prev,next,slot,(endSlot+4)%8);
            fast.IsMotorway=true;fast.MotorwayId=motorway.Id;fast.SpeedLimit=Rules.MotorwaySpeed;fast.Key=$"motorway:{motorway.Id}:{at.X}:{at.Y}";
            var result=new List<Lane>();
            if(local.Distances.Last()>1e-8)result.Add(local);
            result.Add(fast);return result;
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
