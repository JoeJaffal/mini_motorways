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
        public bool IsRailCrossingClosed(Cell c)=>Rules.Version==GameVersion.OriginalReference&&railClosedUntil.TryGetValue(c,out double until)&&Time<=until;
        public Point TrainPoint(TrainState train,double offset=0)=>RailLines[train.LineId].Position(train.Distance-train.Direction*offset);
        void InitializeRailways()
        {
            RailLines.Clear();Trains.Clear();railClosedUntil.Clear();
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
