using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    public sealed class RailLineProfile {public Cell[] Cells;public bool Loop;public int SpawnIndex;}
    public sealed class RailLineState
    {
        public int Id;public Cell[] Cells;public bool Loop;public Lane[] Lanes;public double[] Offsets;public double Length;
        public Point Position(double distance)
        {
            distance=Loop?(distance%Length+Length)%Length:Math.Max(0,Math.Min(Length,distance));
            int index=Array.BinarySearch(Offsets,distance);if(index<0)index=~index-1;index=Math.Min(Lanes.Length-1,Math.Max(0,index));
            return Lanes[index].Position(distance-Offsets[index]);
        }
    }
    public sealed class TrainState
    {public int Id,LineId,Direction=1,LastStation=-1,Stops;public double Distance,Speed,Wait,SinceStation=1000;}
    public sealed class TrainSnapshot
    {public int Id,LineId,Direction,Stops;public double X,Y,Speed,Wait,Distance;}
    public sealed class RailSnapshot {public int Id;public bool Loop;public Cell[] Cells;}
    public sealed partial class TrafficWorld
    {
        public readonly List<RailLineState> RailLines=new List<RailLineState>();
        public readonly List<TrainState> Trains=new List<TrainState>();
        readonly Dictionary<Cell,double> railClosedUntil=new Dictionary<Cell,double>();
        readonly HashSet<(Cell,Cell)> railDiagonalSteps=new HashSet<(Cell,Cell)>();
        public bool IsRailCrossingClosed(Cell c)=>Rules.Version==GameVersion.OriginalReference&&railClosedUntil.TryGetValue(c,out double until)&&Time<=until;
        public Point TrainPoint(TrainState train,double offset=0)=>RailLines[train.LineId].Position(train.Distance-train.Direction*offset);
        void InitializeRailways()
        {
            RailLines.Clear();Trains.Clear();railClosedUntil.Clear();railDiagonalSteps.Clear();
            if(Rules.Version!=GameVersion.OriginalReference||!CityCatalog.Maps.Contains(Scenario))return;
            foreach(var profile in Map.RailLines)
            {
                if(profile.Cells.Length<2)continue;
                var line=new RailLineState{Id=RailLines.Count,Cells=(Cell[])profile.Cells.Clone(),Loop=profile.Loop,Lanes=new Lane[profile.Cells.Length],Offsets=new double[profile.Cells.Length]};
                for(int i=0;i<line.Cells.Length;i++)
                {
                    var c=line.Cells[i];var prev=line.Cells[i==0?(line.Loop?line.Cells.Length-1:0):i-1];var next=line.Cells[i==line.Cells.Length-1?(line.Loop?0:i):i+1];
                    var center=new Point(c);var a=i==0&&!line.Loop?center:(new Point(prev)+center)/2;var b=i==line.Cells.Length-1&&!line.Loop?center:(center+new Point(next))/2;
                    // Independent smooth rail geometry; original spline/fixed-point trace parity is not yet validated.
                    var points=Cubic(a,Point.Lerp(a,center,.8),Point.Lerp(b,center,.8),b,16);
                    var lane=CreateLane(points,c,prev,next,Direction(prev,c),Direction(c,next));line.Offsets[i]=line.Length;line.Length+=lane.Length;line.Lanes[i]=lane;
                }
                RailLines.Add(line);
                for(int i=0;i<line.Cells.Length;i++)
                {
                    if(i==line.Cells.Length-1&&!line.Loop)break;
                    Cell p=line.Cells[i],q=line.Cells[(i+1)%line.Cells.Length];
                    if(p.X!=q.X&&p.Y!=q.Y){railDiagonalSteps.Add((p,q));railDiagonalSteps.Add((q,p));}
                }
                if(profile.SpawnIndex>=0)Trains.Add(new TrainState{Id=Trains.Count,LineId=line.Id,Distance=line.Offsets[profile.SpawnIndex]});
            }
        }
        double ForwardDistance(RailLineState line,double from,double to,int direction)
        {
            double distance=(to-from)*direction;
            return line.Loop?(distance%line.Length+line.Length)%line.Length:distance;
        }
        double StationTarget(RailLineState line,Building station,int direction)
        {
            var indices=Enumerable.Range(0,line.Cells.Length).Where(i=>station.Platform.Contains(line.Cells[i])).ToArray();if(indices.Length==0)return double.NaN;
            // Stop with the leading wheel inside the departure end of the platform.
            var ends=indices.Where(i=>!indices.Contains((i+direction+line.Cells.Length)%line.Cells.Length)).ToArray();
            int end=ends.Length==0?indices[indices.Length-1]:ends[0];
            double front=direction>0?TrainTuning.WheelDistance:TrainTuning.WheelDistance*5+TrainTuning.CarriageGap*2;
            return line.Offsets[end]+line.Lanes[end].Length/2-direction*front;
        }
        void UpdateTrains()
        {
            if(Rules.Version!=GameVersion.OriginalReference)return;
            foreach(var train in Trains)
            {
                var line=RailLines[train.LineId];
                if(train.Wait>0){train.Wait=Math.Max(0,train.Wait-Rules.TickSeconds);UpdateCrossingSignals(train,line);continue;}
                Building target=null;double targetDistance=double.PositiveInfinity;
                foreach(var station in Buildings.Where(b=>b.IsStation&&b.DestinationSlot==0))
                {
                    if(station.CarparkId==train.LastStation&&train.SinceStation<=1)continue;
                    double position=StationTarget(line,station,train.Direction);if(double.IsNaN(position))continue;
                    double distance=ForwardDistance(line,train.Distance,position,train.Direction);
                    if(distance>1e-7&&distance<targetDistance){target=station;targetDistance=distance;}
                }
                if(!line.Loop)
                {
                    double end=train.Direction>0?line.Length-TrainTuning.BufferDistance:TrainTuning.BufferDistance;
                    double distance=ForwardDistance(line,train.Distance,end,train.Direction);
                    if(distance>=0&&distance<targetDistance){target=null;targetDistance=distance;}
                }
                double braking=train.Speed*train.Speed/(2*TrainTuning.Deceleration);
                bool stopping=targetDistance<=braking+1e-6;
                double acceleration=stopping?-train.Speed*train.Speed/(2*Math.Max(1e-8,targetDistance)):TrainTuning.Acceleration;
                double speed=Math.Max(stopping?TrainTuning.MinimumSpeed:0,Math.Min(TrainTuning.Speed,train.Speed+acceleration*Rules.TickSeconds));
                double travel=speed*Rules.TickSeconds;int movementDirection=train.Direction;
                if(travel>=targetDistance)
                {
                    travel=targetDistance;speed=0;train.Wait=TrainTuning.StationWait;train.Stops++;
                    if(target!=null){train.LastStation=target.CarparkId;train.SinceStation=0;GenerateStationDemand(target);}
                    else if(!line.Loop)train.Direction=-train.Direction;
                }
                train.Distance+=movementDirection*travel;train.SinceStation+=travel;train.Speed=speed;
                train.Distance=line.Loop?(train.Distance%line.Length+line.Length)%line.Length:Math.Max(0,Math.Min(line.Length,train.Distance));
                UpdateCrossingSignals(train,line);
            }
            foreach(var cell in railClosedUntil.Where(p=>p.Value<Time).Select(p=>p.Key).ToArray())railClosedUntil.Remove(cell);
        }
        void UpdateCrossingSignals(TrainState train,RailLineState line)
        {
            double front=train.Direction>0?TrainTuning.WheelDistance:TrainTuning.WheelDistance*5+TrainTuning.CarriageGap*2;
            double rear=train.Direction>0?TrainTuning.WheelDistance*5+TrainTuning.CarriageGap*2:TrainTuning.WheelDistance;
            for(int i=0;i<line.Cells.Length;i++)
            {
                double along=ForwardDistance(line,train.Distance,line.Offsets[i]+line.Lanes[i].Length/2,train.Direction);
                if(line.Loop&&along>line.Length/2)along-=line.Length;
                if(along>=-rear-.5&&along<=front+TrainTuning.SignalDistance+.5)railClosedUntil[line.Cells[i]]=Time+TrainTuning.CrossingWait;
            }
        }
        void GenerateStationDemand(Building station)
        {
            var destinations=Buildings.Where(b=>b.IsStation&&b.CarparkId==station.CarparkId).ToArray();
            double houses=Buildings.Count(h=>h.IsHouse&&destinations.Any(d=>d.Color==h.Color));
            double[] weights=destinations.Select(d=>OriginalDemandInterval(d)*d.PlannedDemandMultiplier).ToArray();double total=weights.Sum();
            for(int i=0;i<destinations.Length;i++)
            {
                int pins=(int)Math.Round(weights[i]/total*houses*TrainTuning.DemandPerHouse,MidpointRounding.AwayFromZero);
                pins=Math.Max(TrainTuning.MinimumDemand,Math.Min(TrainTuning.MaximumDemand,pins));
                var destination=destinations[i];destination.Demand=Math.Min(DestinationCapacity(destination)+DestinationOverflow(destination),destination.Demand+pins);
            }
        }
        // Original TrainCrossingModel chunks: a road tile over a rail tile, or the tile corner where a diagonal road passes
        // between the two tiles of a diagonal rail step (LaneUpdateProcess).
        bool RailCornerCells(Lane lane,out Cell r1,out Cell r2)
        {
            r1=r2=default;if(lane.Corner==null||railDiagonalSteps.Count==0)return false;
            var code=lane.Corner.Value;int x=(-code.X-3)/2,y=(-code.Y-3)/2;
            Cell a=new Cell(x,y),b=new Cell(x+1,y+1),c=new Cell(x+1,y),d=new Cell(x,y+1);
            bool roadAB=lane.Tile==a||lane.Tile==b;r1=roadAB?c:a;r2=roadAB?d:b;
            return railDiagonalSteps.Contains((r1,r2));
        }
        bool IsRailChunk(Lane lane)
        {
            if(Rules.Version!=GameVersion.OriginalReference||lane==null||lane.IsMotorway||lane.IsParking)return false;
            if(lane.Corner!=null)return RailCornerCells(lane,out _,out _);
            return InBounds(lane.Tile)&&Rails[lane.Tile.X,lane.Tile.Y];
        }
        bool RailChunkClosed(Lane lane)=>lane.Corner!=null?RailCornerCells(lane,out var r1,out var r2)&&(IsRailCrossingClosed(r1)||IsRailCrossingClosed(r2)):IsRailCrossingClosed(lane.Tile);
        double DistanceToLane(Vehicle car,Lane lane)
        {
            if(!car.Moving)return double.PositiveInfinity;double distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++){if(ReferenceEquals(car.Lanes[i],lane))return distance;distance+=car.Lanes[i].Length;}
            return double.PositiveInfinity;
        }
        double DistanceToCar(Vehicle car,int otherId)
        {
            var other=CarById(otherId);if(!car.Moving||other==null||!other.Moving)return double.PositiveInfinity;
            if(other.CurrentLane.Key==car.CurrentLane.Key)return other.DistanceAlongLane-car.DistanceAlongLane;
            double distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+8);i++)
            {if(car.Lanes[i].Key==other.CurrentLane.Key)return distance+other.DistanceAlongLane;distance+=car.Lanes[i].Length;}
            return double.PositiveInfinity;
        }
        // Original RoadChunkModel.CanInboundVehicleEnter, train crossing part (before every other test). Unless the car is
        // already on an open crossing: a closed crossing refuses it (except a tile-corner crossing less than one vehicle
        // length ahead); an open one refuses it while a car on a conflicting lane of a chunk along its path is stopped or
        // within three vehicle lengths of the vehicle blocking it. The scan starts at the car's next lane and stops after
        // the first chunk that is not a crossing (a chunk of two lanes or fewer has no traversing list and is not scanned).
        const double CarStoppedSpeed=.0005; // CarStoppedSpeedThreshold 0.001 world units/s
        bool RailCrossingAllows(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out string why)
        {
            why="";if(!IsRailChunk(lane))return true;
            // Original: the checks are skipped while the car's own chunk is a closed crossing (TrainSignalState 0 is
            // Closed), so a car caught on the tracks may always move on.
            if(car.Moving&&IsRailChunk(car.CurrentLane)&&RailChunkClosed(car.CurrentLane))return true;
            if(RailChunkClosed(lane))
            {
                if(lane.Corner!=null&&DistanceToLane(car,lane)<=Rules.CarLength)return true;
                why="Train crossing";return false;
            }
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)
            {
                var pathLane=car.Lanes[i];bool rail=IsRailChunk(pathLane);
                if(rail||!pathLane.IsParking&&!pathLane.IsMotorway&&!ChunkHasFewLanes(pathLane.ChunkCell))
                    foreach(var other in snapshot)
                    {
                        if(other.Car.Id==car.Id||other.Lane.IsParking||other.Lane.IsMotorway||other.Lane.ChunkCell!=pathLane.ChunkCell)continue;
                        if(other.Lane.Incoming>=8||pathLane.Incoming>=8||!ConnectionsIntersect(other.Lane,pathLane,false,false))continue;
                        int blocking=other.Car.BlockingVehicle;if(blocking<0)continue;
                        double gap=other.Car.ObstacleState==ObstacleKind.Leader?other.Car.ObstacleDistance:DistanceToCar(other.Car,blocking);
                        if(gap<3*Rules.CarLength||other.Speed<CarStoppedSpeed){why="Crossing congested";return false;}
                    }
                if(!rail)break;
            }
            return true;
        }
        // Original blocked-chunk stopping point: IntersectionStoppingOffset (one vehicle length less half a minimum gap) past
        // the chunk start, none for a tile corner; a crossing beyond the next lane is approached crossingStopDistance (1.8)
        // vehicle lengths shorter, and a corner crossing a further IntersectionStoppingOffset shorter. Returned as our stop
        // distance (front travel before the hold), from the distance to the chunk start.
        double OriginalBlockedStop(Lane next,bool immediate,double ahead)
        {
            double iso=Rules.CarLength-Rules.FollowingGap*.5,offset=next.Corner!=null?0:iso;
            if(!immediate&&IsRailChunk(next))offset=-1.8*Rules.CarLength-(next.Corner!=null?iso:0);
            return Math.Max(0,ahead+offset-Rules.CarLength);
        }
        public bool CanConnectAcrossRail(Cell from,Cell to)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return true;
            foreach(var c in new[]{from,to})
            {
                if(!Rails[c.X,c.Y]||BuildingAt(c)!=null)continue;
                var line=RailLines.FirstOrDefault(l=>l.Cells.Contains(c));if(line==null)continue;
                int i=Array.IndexOf(line.Cells,c);var lane=line.Lanes[i];int incoming=Direction(lane.Previous,c),outgoing=Direction(c,lane.Next),d=Direction(from,to);
                if(incoming!=outgoing||outgoing%2!=0||d%2!=0||(d%4)==(outgoing%4))return Reject("Roads must cross straight rail at a right angle");
            }
            return true;
        }
        public int DestinationOverflow(Building shop)=>Rules.Version==GameVersion.OriginalReference&&shop.Upgraded?6:Rules.MaximumOverflowPins;
    }
}
