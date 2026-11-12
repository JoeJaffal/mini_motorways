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
        // U-turn or ring lane (a ring tile's exit lane can take it; connection.IsRoundabout means ring-to-ring).
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
            if(incoming<8&&!uTurn&&InBounds(next)&&RoadDegree(next)>=3&&Tile(next)!=Infrastructure.TrafficLight&&RoundaboutAt(next)==null)
                speed*=Rules.IntersectionMultiplier;
            return speed;
        }

        // The original counts a motorway's slot on its end tile as a road connection (RoadTileSignature).
        int RoadDegree(Cell tile)=>Degree(tile)+Motorways.Count(m=>!m.PendingRemoval&&(m.Start==tile||m.End==tile));

        // Original NumberOfRoadsAtIntersectionToSlowDownFor: distinct roads at the chunk, ignoring house driveways,
        // carpark entrances and roundabout lanes (IgnoreHouses/IgnoreDestinationsForIntersectionSlowDown = 1).
        int RoadsForIntersectionSlowdown(Cell tile)
        {
            if(tile.X<0)return IsCrossingCorner(tile)?4:0;
            if(!InBounds(tile)||RoundaboutAt(tile)!=null)return 0;
            int mask=Connections[tile.X,tile.Y],count=0;
            for(int d=0;d<8;d++)
            {
                if((mask&(1<<d))==0)continue;var other=tile+Directions[d];
                if(AccessBuildingAt(other)!=null||RoundaboutAt(other)!=null)continue;
                count++;
            }
            return count+Motorways.Count(m=>!m.PendingRemoval&&(m.Start==tile||m.End==tile));
        }

        // Original RoadTileConnection.IntersectsOtherConnection (right-hand traffic, smallIntersection = true), decided
        // from the sides a lane enters and leaves its tile: same exit conflicts (unless crossing in front of a stopped
        // car is allowed and the entries differ), same entry never conflicts, exact reversal never conflicts, a lane
        // conflicts with the other's half-turn rotation, otherwise the lanes cross when exactly one of the other's
        // sides lies clockwise from this lane's entry through its exit. Our direction indices are clockwise like the
        // original's, so the cyclic test needs no remapping.
        static bool ConnectionsIntersect(Lane a,Lane b,bool allowCrossingInFrontOfOther,bool smallIntersection=true)
        {
            int ai=(a.Incoming+4)%8,ao=a.Outgoing,bi=(b.Incoming+4)%8,bo=b.Outgoing;
            if(ao==bo&&(!allowCrossingInFrontOfOther||ai==bi))return true;
            if(ai==bi)return false;
            if(ai==bo&&ao==bi)return false;
            if(smallIntersection&&!b.IsMotorway&&ai==(bi+4)%8&&ao==(bo+4)%8)return true;
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
            int slot=RampDirection(motorway,at),endSlot=RampDirection(motorway,next);
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

        // Original tile corners (LaneUpdateProcess, TileCornerModel): a diagonal step between two ordinary road tiles
        // runs through a corner chunk. Each tile's lane ends 0.5 tiles from its centre and a short corner lane
        // (about 0.41 tiles) joins them. The corner chunk holds two lanes, so it is never arbitrated; the tile lane before
        // it has a single outbound lane and takes only its turn factor, while the corner lane takes the intersection
        // factor when the next tile offers several ways.
        // Crossing diagonals make a four-node corner chunk: a junction where every pair of nodes except a U-turn is a
        // lane (RoadTileSignature.AddNode), so cars cross and also turn onto the other diagonal there. Corner chunks have
        // a code cell (negative coordinates, never a real tile); their lanes arbitrate among themselves and are not
        // controlled by a light on a neighbouring tile.
        static Cell CornerCode(Cell a,Cell b)=>new Cell(-(a.X+b.X+2),-(a.Y+b.Y+2));
        bool Linked(Cell a,Cell b)=>InBounds(a)&&InBounds(b)&&a!=b&&Math.Abs(a.X-b.X)<=1&&Math.Abs(a.Y-b.Y)<=1&&(Connections[a.X,a.Y]&(1<<Direction(a,b)))!=0;
        bool IsCrossingCorner(Cell code)
        {
            if(Rules.Version!=GameVersion.OriginalReference||code.X>=0||code.Y>=0)return false;
            int x=(-code.X-3)/2,y=(-code.Y-3)/2;
            Cell a=new Cell(x,y),b=new Cell(x+1,y+1),c=new Cell(x+1,y),d=new Cell(x,y+1);
            return Linked(a,b)&&Linked(c,d)&&SplitsCorner(a,b)&&SplitsCorner(c,d);
        }
        // A turn at a crossing corner from tile a to its orthogonal neighbour c: the car leaves a along the diagonal
        // a->b and enters c as if from d (the other diagonal, d->c). Our routes list cells, so such a step is an
        // orthogonal step without a direct link; where a and c are also linked directly the direct link is used, and
        // with crossings on both sides of the a-c edge the first side is used.
        bool CornerTurn(Cell a,Cell c,out Cell b,out Cell d)
        {
            b=d=a;
            if(Rules.Version!=GameVersion.OriginalReference||!InBounds(a)||!InBounds(c))return false;
            int dx=c.X-a.X,dy=c.Y-a.Y;if(Math.Abs(dx)+Math.Abs(dy)!=1||Linked(a,c))return false;
            for(int s=-1;s<=1;s+=2)
            {
                var side=dx!=0?new Cell(0,s):new Cell(s,0);
                var bb=c+side;var dd=a+side;
                if(InBounds(bb)&&InBounds(dd)&&IsCrossingCorner(CornerCode(a,bb))){b=bb;d=dd;return true;}
            }
            return false;
        }
        // Route step p->q uses the link edge (a corner turn uses half of each crossing diagonal it joins).
        bool StepUsesEdge(Cell p,Cell q,(Cell,Cell) edge)
        {
            if(RoadEdge(p,q)==edge)return true;
            if(Rules.Version!=GameVersion.OriginalReference||Math.Abs(p.X-q.X)+Math.Abs(p.Y-q.Y)!=1||Linked(p,q))return false;
            for(int s=-1;s<=1;s+=2)
            {
                var side=p.X!=q.X?new Cell(0,s):new Cell(s,0);
                if(RoadEdge(p,q+side)==edge||RoadEdge(p+side,q)==edge)return true;
            }
            return false;
        }
        // Travel time of a corner turn for route costs: half a diagonal at the tile's lane speed, then half at turn speed.
        double CornerTurnTime(Cell a,int incoming,Cell c,bool forCost)
        {
            CornerTurn(a,c,out var b,out var d);int exit=Direction(a,b),arrive=Direction(d,c);
            return Math.Sqrt(.5)/Math.Max(.01,LaneSpeed(a,incoming,exit,false,forCost))+Math.Sqrt(.5)/Math.Max(.01,OriginalTurnSpeed(exit,arrive,false));
        }
        Lane CornerTurnLane(Cell at,Cell c,Cell b,Cell d,Point start)
        {
            int dirIn=Direction(at,b),dirOut=Direction(d,c);
            var hin=DirectionVector(dirIn);var hout=DirectionVector(dirOut);
            var finish=new Point(c)-hout*.5+hout.Right*Rules.LaneOffset;
            double handle=Point.Distance(start,finish)*.4;
            var lane=CreateLane(Cubic(start,start+hin*handle,finish-hout*handle,finish,8),at,at,c,dirIn,dirOut);
            lane.IsCorner=true;lane.IsJunction=true;lane.Corner=CornerCode(at,b);lane.Key=$"cornerturn:{at.X}:{at.Y}:{c.X}:{c.Y}";
            bool several=RoadDegree(c)>=3&&Tile(c)!=Infrastructure.TrafficLight&&RoundaboutAt(c)==null;
            lane.SpeedLimit=OriginalTurnSpeed(dirIn,dirOut,false)*(several?Rules.IntersectionMultiplier:1);
            return lane;
        }
        bool SplitsCorner(Cell a,Cell b)=>Rules.Version==GameVersion.OriginalReference&&a.X!=b.X&&a.Y!=b.Y&&
            RoundaboutAt(a)==null&&RoundaboutAt(b)==null&&MotorwayBetween(a,b)==null&&SharedTransitBetween(a,b)==null;

        double OriginalTurnSpeed(int incoming,int outgoing,bool fromMotorway)
        {
            double speed=Rules.CarSpeed;
            if(incoming<8&&!fromMotorway){int turn=Math.Abs(incoming-outgoing);turn=Math.Min(turn,8-turn);if(turn==2)speed*=Rules.RightAngleMultiplier;else if(turn>=3)speed*=Rules.SharpTurnMultiplier;}
            return speed;
        }

        Lane CornerLane(Cell at,Cell next,int direction,Point start,Point heading)
        {
            var finish=new Point(next)-heading*.5+heading.Right*Rules.LaneOffset;
            var points=new Point[5];for(int k=0;k<5;k++)points[k]=start+(finish-start)*(k/4.0);
            var lane=CreateLane(points,at,at,next,direction,direction);
            lane.IsCorner=true;lane.Key=$"corner:{at.X}:{at.Y}:{direction}";lane.Corner=CornerCode(at,next);lane.IsJunction=IsCrossingCorner(lane.Corner.Value);
            lane.SpeedLimit=OriginalLaneSpeed(at,direction,direction,false,false);
            return lane;
        }

        bool IsControlledLane(Lane lane)=>lane!=null&&!lane.IsParking&&!lane.IsMotorway&&Signals.ContainsKey(lane.ChunkCell);

        // Original maximum acceleration: roundabout if the current or next chunk is a roundabout; controlled if the
        // current or next chunk is signal-controlled or the car's own driveway, or near the end of a motorway lane.
        const double CrossingAcceleration=.1; // 0.2 world units/s^2
        double OriginalMaximumAcceleration(Vehicle car,Lane current,double distanceAlong)
        {
            var next=car.RouteIndex+1<car.Lanes.Count?car.Lanes[car.RouteIndex+1]:null;
            if(current.IsRoundabout||next!=null&&next.IsRoundabout)return Rules.RoundaboutAcceleration;
            if(IsRailChunk(current)||IsRailChunk(next))return CrossingAcceleration; // maxAccelerationOnCrossings
            var home=car.HomeId>=0&&car.HomeId<Buildings.Count?Buildings[car.HomeId].Cell:new Cell(-1,-1);
            bool driveway=!current.IsParking&&current.Tile==home||next!=null&&!next.IsParking&&next.Tile==home;
            bool motorwayEnd=current.IsMotorway&&current.Length-distanceAlong<Rules.CarLength;
            return driveway||IsControlledLane(current)||IsControlledLane(next)||motorwayEnd?Rules.ControlledAcceleration:Rules.MaxAcceleration;
        }
    }
}
