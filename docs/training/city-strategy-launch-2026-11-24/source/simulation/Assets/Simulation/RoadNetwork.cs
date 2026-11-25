using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly Dictionary<(Cell,Cell,bool,int),List<Cell>> routeCache=new Dictionary<(Cell,Cell,bool,int),List<Cell>>();

        public IEnumerable<Cell> Neighbors(Cell at,Cell start,Cell goal)=>Neighbors(at,start,goal,false);
        IEnumerable<Cell> Neighbors(Cell at,Cell start,Cell goal,bool retired)
        {
            if(!InBounds(at))yield break;
            var currentBuilding=BuildingAt(at);
            if(currentBuilding!=null&&at!=start&&at!=goal&&(!currentBuilding.SharedLot||Rules.Version!=GameVersion.OriginalReference))yield break;
            if(currentBuilding!=null&&currentBuilding.SharedLot&&Rules.Version==GameVersion.OriginalReference&&HasAccess(currentBuilding,at))
                foreach(var exit in Accesses(currentBuilding))if(exit!=at)yield return exit;
            var round=RoundaboutAt(at);
            int ringIndex=round==null?-1:Array.IndexOf(round.Ring,at);
            foreach(var m in Motorways.Where(m=>(retired||!m.PendingRemoval)&&(m.Start==at||m.End==at)))
            {var end=m.Other(at);if(CanTraverse(end,retired)&&(retired||!PendingRemoval[at.X,at.Y]))yield return end;}
            for(int d=0;d<8;d++)
            {
                if((Connections[at.X,at.Y]&(1<<d))==0)continue;
                var next=at+Directions[d];
                if(!CanTraverse(next,retired)||!retired&&PendingRemoval[at.X,at.Y])continue;
                var b=BuildingAt(next);if(b!=null&&next!=goal&&next!=start&&(!b.SharedLot||Rules.Version!=GameVersion.OriginalReference))continue;
                if(ringIndex>=0&&round.Ring.Contains(next)&&next!=round.Ring[(ringIndex+1)%4])continue;
                yield return next;
            }
            if(Rules.Version==GameVersion.OriginalReference&&(retired||!PendingRemoval[at.X,at.Y]))
                for(int d=0;d<8;d+=2)
                {
                    var next=at+Directions[d];
                    if(!CornerTurn(at,next,out _,out _)||!CanTraverse(next,retired))continue;
                    var b=BuildingAt(next);if(b!=null&&next!=goal&&next!=start&&!b.SharedLot)continue;
                    yield return next;
                }
        }

        public List<Cell> FindRoute(Cell start,Cell goal)=>FindRoute(start,goal,false);
        public List<Cell> FindRoute(Cell start,Cell goal,bool allowRetired)=>FindRoute(start,goal,allowRetired,8);
        // startDirection: heading into start (8 = none). Original U-turn lanes exist only on dead-end tiles (one road
        // connection), so OriginalReference never reverses elsewhere and a re-route keeps the car's heading.
        List<Cell> FindRoute(Cell start,Cell goal,bool allowRetired,int startDirection)
        {
            if(!InBounds(start)||!InBounds(goal))return new List<Cell>();
            if(Rules.Version!=GameVersion.OriginalReference)startDirection=8;
            var key=(start,goal,allowRetired,startDirection);
            if(routeCache.TryGetValue(key,out var cached))return new List<Cell>(cached);
            var origin=(cell:start,dir:startDirection);
            var queue=new MinQueue<(Cell cell,int dir)>();queue.Push(origin,0);
            var costs=new Dictionary<(Cell,int),double>{{origin,0}};
            var previous=new Dictionary<(Cell,int),(Cell,int)>();
            var closed=new HashSet<(Cell,int)>();
            while(queue.Count>0)
            {
                var state=queue.Pop();if(!closed.Add(state))continue;
                if(state.cell==goal)
                {
                    var route=new List<Cell>{goal};
                    while(state!=origin){state=previous[state];route.Add(state.cell);}route.Reverse();
                    routeCache[key]=route;return new List<Cell>(route);
                }
                foreach(var next in Neighbors(state.cell,start,goal,allowRetired))
                {
                    if(next!=goal&&InPlannedRoundabout(next))continue; // a planned roundabout has no usable lanes yet
                    int direction=Direction(state.cell,next),exit=direction;
                    bool turn=CornerTurn(state.cell,next,out var turnB,out var turnD);
                    if(turn){exit=Direction(state.cell,turnB);direction=Direction(turnD,next);}
                    var target=(cell:next,dir:direction);
                    if(closed.Contains(target))continue;
                    var motorway=MotorwayBetween(state.cell,next);
                    double speed=motorway==null?LaneSpeed(state.cell,state.dir,exit):Rules.MotorwaySpeed;
                    var transit=SharedTransitBetween(state.cell,next);
                    double cost=turn?CornerTurnTime(state.cell,state.dir,next,false):
                        motorway!=null&&Rules.Version==GameVersion.OriginalReference?MotorwayStepTime(state.cell,state.dir,motorway,next):
                        StepLength(state.cell,state.dir,exit,next,motorway,transit)/Math.Max(.01,speed);
                    if(state.dir<8&&((exit-state.dir+8)%8)==4)
                    {
                        if(Rules.Version!=GameVersion.OriginalReference)cost+=500;
                        else if(RoadDegree(state.cell)>1)continue;
                    }
                    if(allowRetired&&(PendingRemoval[next.X,next.Y]||PendingRemoval[state.cell.X,state.cell.Y]))cost+=100000;
                    // The original charges a mothballed motorway lane like any mothballed lane (100000), so re-routing cars
                    // only keep using a retired motorway when nothing else reaches their goal.
                    else if(allowRetired&&motorway!=null&&motorway.PendingRemoval&&Rules.Version==GameVersion.OriginalReference)cost+=100000;
                    double total=costs[state]+(transit!=null?SharedTransitCost(transit,state.cell,next):Math.Max(1,Math.Floor(10*cost)));
                    if(!costs.TryGetValue(target,out var old)||total<old)
                    {costs[target]=total;previous[target]=state;queue.Push(target,total);}
                }
            }
            routeCache[key]=new List<Cell>();return new List<Cell>();
        }

        // The original measures a house's dispatch cost from the end of its driveway lane, so the step out of the house
        // tile is not charged when choosing which house serves a destination.
        double FirstStepCost(IList<Cell> route)
        {
            if(route.Count<2||MotorwayBetween(route[0],route[1])!=null||SharedTransitBetween(route[0],route[1])!=null)return 0;
            return Math.Max(1,Math.Floor(10*Distance(route[0],route[1])/LaneSpeed(route[0],8,Direction(route[0],route[1]),false,true)));
        }

        public double RouteCost(IList<Cell> route)
        {
            if(route.Count<2)return double.PositiveInfinity;double total=0;
            for(int i=0;i<route.Count-1;i++)
            {int incoming=i==0?8:CornerTurn(route[i-1],route[i],out _,out var arrivedFrom)?Direction(arrivedFrom,route[i]):Direction(route[i-1],route[i]);int outgoing=Direction(route[i],route[i+1]);
                if(CornerTurn(route[i],route[i+1],out _,out _)){total+=Math.Max(1,Math.Floor(10*CornerTurnTime(route[i],incoming,route[i+1],true)));continue;}
                double speed=MotorwayBetween(route[i],route[i+1])==null?LaneSpeed(route[i],incoming,outgoing,i>0&&MotorwayBetween(route[i-1],route[i])!=null,true):Rules.MotorwaySpeed;
                var transit=SharedTransitBetween(route[i],route[i+1]);if(transit!=null){total+=SharedTransitCost(transit,route[i],route[i+1]);continue;}
                var mw=MotorwayBetween(route[i],route[i+1]);
                total+=Math.Max(1,Math.Floor(10*(mw!=null&&Rules.Version==GameVersion.OriginalReference?MotorwayStepTime(route[i],incoming,mw,route[i+1]):StepLength(route[i],incoming,outgoing,route[i+1],mw,null)/speed)));}
            return total;
        }
        public double LaneSpeed(Cell at,int incoming,int outgoing,bool fromMotorway=false,bool forCost=false)
        {
            if(Rules.Version==GameVersion.OriginalReference)return OriginalLaneSpeed(at,incoming,outgoing,fromMotorway,forCost);
            double speed=Rules.CarSpeed;
            if(RoundaboutAt(at)!=null)return speed*Rules.RoundaboutMultiplier;
            if(incoming<8)
            {
                int turn=Math.Abs(incoming-outgoing);turn=Math.Min(turn,8-turn);
                if(turn==2)speed*=Rules.RightAngleMultiplier;else if(turn>=3)speed*=Rules.SharpTurnMultiplier;
            }
            // Signal-controlled intersections avoid the uncontrolled junction slowdown.
            if(Degree(at)>=3&&Tile(at)!=Infrastructure.TrafficLight)speed*=Rules.IntersectionMultiplier;
            return speed;
        }

        public List<Lane> MakeLanes(IList<Cell> route)
        {
            var lanes=new List<Lane>();
            for(int i=0;i<route.Count;i++)
            {
                Cell at=route[i],prev=i==0?at:route[i-1],next=i==route.Count-1?at:route[i+1];
                // A corner turn (CornerTurn): this tile's lane runs toward the crossing corner along its diagonal, a turning
                // corner lane follows, and the next tile's lane starts as if arriving along the other diagonal.
                Cell turnTo=next,turnB=at,turnD=at;bool turnOut=i<route.Count-1&&CornerTurn(at,next,out turnB,out turnD);
                if(turnOut)next=turnB;
                if(i>0&&CornerTurn(prev,at,out _,out var arrivedFrom))prev=arrivedFrom;
                var transit=SharedTransitBetween(at,next);
                if(transit!=null){lanes.AddRange(ParkingTransitRoute(transit,at,next));i++;continue;}
                Point center=new Point(at),a=new Point(prev),b=new Point(next);
                Point incoming=(center-a).Unit,outgoing=(b-center).Unit;
                bool fromMotorway=i>0&&MotorwayBetween(prev,at)!=null;
                var motorway=i<route.Count-1?MotorwayBetween(at,next):null;
                Point start=i==0?center:fromMotorway?center+incoming.Right*Rules.LaneOffset:(a+center)/2+incoming.Right*Rules.LaneOffset;
                Point end=i==route.Count-1?center:(b+center)/2+outgoing.Right*Rules.LaneOffset;
                if(Rules.Version==GameVersion.OriginalReference)
                {
                    var parcel=AccessBuildingAt(at);
                    if(parcel!=null&&!parcel.IsHouse)
                    {
                        if(i==0)start=ParkingAccessPoint(parcel,at,false);
                        if(i==route.Count-1)end=ParkingAccessPoint(parcel,at,true);
                    }
                }
                int inDir=i==0?8:Direction(prev,at),outDir=i==route.Count-1?inDir:Direction(at,next);
                if(Rules.Version==GameVersion.OriginalReference&&fromMotorway)
                {
                    // Original: the end tile's lane starts at the motorway's slot edge and runs across the whole tile.
                    int slot=RampDirection(MotorwayBetween(prev,at),at);var travel=DirectionVector((slot+4)%8);
                    inDir=(slot+4)%8;incoming=travel;start=SlotPoint(at,slot)+travel.Right*Rules.LaneOffset;
                }
                if(Rules.Version==GameVersion.OriginalReference&&motorway!=null)
                {
                    lanes.AddRange(OriginalMotorwayStart(motorway,at,prev,next,start,incoming,inDir));
                    continue;
                }
                var round=RoundaboutAt(at);
                bool cornerIn=i>0&&!fromMotorway&&SplitsCorner(prev,at),cornerOut=i<route.Count-1&&motorway==null&&SplitsCorner(at,next);
                if(cornerIn&&!(i==0))start=center-incoming*.5+incoming.Right*Rules.LaneOffset;
                if(cornerOut&&!(i==route.Count-1))end=center+outgoing*.5+outgoing.Right*Rules.LaneOffset;
                Point[] samples;
                if(motorway!=null)
                {
                    Point finish=b+outgoing.Right*Rules.LaneOffset;
                    double handle=Math.Min(2,Point.Distance(start,finish)*.3);
                    samples=Cubic(start,start+incoming*handle,finish-outgoing*handle,finish,Math.Max(24,(int)(Distance(at,next)*8)));
                }
                else if(round!=null&&at!=round.Center)
                {
                    samples=RoundaboutSamples(round,at,prev,next,start,end,incoming,outgoing);
                }
                else
                {
                    double length=Point.Distance(start,end);
                    samples=Cubic(start,start+incoming*Math.Min(.35,length*.45),end-outgoing*Math.Min(.35,length*.45),end,12);
                }
                var lane=CreateLane(samples,at,prev,next,inDir,outDir);
                lane.SpeedLimit=LaneSpeed(at,inDir,outDir<8?outDir:0,fromMotorway);
                lane.IsJunction=Degree(at)>=3||Tile(at)==Infrastructure.TrafficLight;
                lane.IsRoundabout=round!=null;
                if(motorway!=null){lane.IsMotorway=true;lane.MotorwayId=motorway.Id;lane.IsJunction=false;lane.SpeedLimit=Rules.MotorwaySpeed;lane.Key=$"motorway:{motorway.Id}:{at.X}:{at.Y}";}
                else if(fromMotorway){lane.IsJunction=true;lane.MotorwayNode=true;}
                // A boundary-based parcel endpoint can coincide with the next lane
                // boundary. Do not create a zero-length lane with an undefined heading.
                if(cornerOut)lane.SpeedLimit=OriginalTurnSpeed(inDir,outDir,fromMotorway)*(IsCrossingCorner(CornerCode(at,next))?Rules.IntersectionMultiplier:1);
                if(lane.Distances.Last()<1e-8&&route.Count>1)continue;
                lanes.Add(lane);
                if(cornerOut)lanes.Add(turnOut?CornerTurnLane(at,turnTo,turnB,turnD,end):CornerLane(at,next,outDir,end,outgoing));
            }
            return lanes;
        }
        // Original atlas uses normalized diagonal boundary points, relative to a centre two world units away.
        // Convert that radius to our tile units; rendering uses the same centreline.
        public static readonly double RoundaboutLaneRadius=Math.Sqrt(5-2*Math.Sqrt(2))/2;
        Point[] RoundaboutSamples(RoundaboutState round,Cell at,Cell prev,Cell next,Point start,Point end,Point incoming,Point outgoing)
        {
            var origin=new Point(round.Center);var radial=(new Point(at)-origin).Unit;
            var middle=origin+radial*RoundaboutLaneRadius;var tangent=new Point(radial.Y,-radial.X);
            var points=new List<Point>();
            void Arc(Point a,Point b)
            {
                double angle=Math.Atan2(a.Y-origin.Y,a.X-origin.X),finish=Math.Atan2(b.Y-origin.Y,b.X-origin.X);
                while(finish>angle+1e-8)finish-=Math.PI*2;
                for(int i=0;i<=10;i++){double t=angle+(finish-angle)*i/10;points.Add(origin+new Point(Math.Cos(t),Math.Sin(t))*RoundaboutLaneRadius);}
            }
            if(round.Ring.Contains(prev))Arc(origin+(new Point(prev)-origin+radial).Unit*RoundaboutLaneRadius,middle);
            else points.AddRange(Cubic(start,start+incoming*.2,middle-tangent*.2,middle,10));
            if(round.Ring.Contains(next))Arc(middle,origin+(new Point(next)-origin+radial).Unit*RoundaboutLaneRadius);
            else points.AddRange(Cubic(middle,middle+tangent*.2,end-outgoing*.2,end,10));
            return points.ToArray();
        }
        static Lane CreateLane(Point[] points,Cell tile,Cell previous,Cell next,int incoming,int outgoing)
        {
            var lane=new Lane{Samples=points,Distances=new double[points.Length],Tile=tile,Previous=previous,Next=next,
                Incoming=incoming,Outgoing=outgoing,Key=$"{tile.X}:{tile.Y}:{incoming}:{outgoing}"};
            for(int i=1;i<points.Length;i++)lane.Distances[i]=lane.Distances[i-1]+Point.Distance(points[i-1],points[i]);
            lane.Length=Math.Max(.001,lane.Distances.Last());return lane;
        }
        // Original LaneModel.PathfindingCost charges a lane its actual length over its speed limit. On an ordinary road tile
        // the step's length is the length of our tile lane for that entry and exit (a right turn is shorter than a left
        // turn), plus the corner lane on a diagonal exit; elsewhere (start, motorway, roundabout, parcel) the
        // centre-to-centre distance is kept.
        static readonly Dictionary<(int,int),double> stepLengthCache=new Dictionary<(int,int),double>();
        // Original motorway costs: the start tile's lane to the ramp at its own speed, then the bespoke motorway lane
        // between the two ramp slots (about one tile shorter than centre to centre) at motorway speed.
        double MotorwayStepTime(Cell at,int inDir,MotorwayState motorway,Cell next)
        {
            int slot=RampDirection(motorway,at);
            double local=inDir<8?TileLaneLength(inDir,slot,false)/Math.Max(.01,OriginalTurnSpeed(inDir,slot,false)):.5/Rules.CarSpeed;
            return local+Math.Max(0,Distance(at,next)-1)/Rules.MotorwaySpeed;
        }
        double TileLaneLength(int inDir,int outDir,bool corner)
        {
            var inc=new Point(Directions[inDir].X,Directions[inDir].Y).Unit;var outv=new Point(Directions[outDir].X,Directions[outDir].Y).Unit;
            var center=new Point(0,0);var a=center-new Point(Directions[inDir].X,Directions[inDir].Y);var b=center+new Point(Directions[outDir].X,Directions[outDir].Y);
            var start=inDir%2==1?center-inc*.5+inc.Right*Rules.LaneOffset:(a+center)/2+inc.Right*Rules.LaneOffset;
            var end=outDir%2==1?center+outv*.5+outv.Right*Rules.LaneOffset:(b+center)/2+outv.Right*Rules.LaneOffset;
            double chord=Point.Distance(start,end);var samples=Cubic(start,start+inc*Math.Min(.35,chord*.45),end-outv*Math.Min(.35,chord*.45),end,12);
            double length=0;for(int i=1;i<samples.Length;i++)length+=Point.Distance(samples[i-1],samples[i]);
            if(corner&&outDir%2==1)length+=Math.Sqrt(2)-1; // corner lane
            return length;
        }
        double StepLength(Cell at,int inDir,int outDir,Cell next,MotorwayState motorway,Building transit)
        {
            if(Rules.Version!=GameVersion.OriginalReference||inDir>=8||outDir>=8||motorway!=null||transit!=null||
                RoundaboutAt(at)!=null||RoundaboutAt(next)!=null||BuildingAt(at)!=null||BuildingAt(next)!=null||MotorwayBetween(new Cell(at.X-Directions[inDir].X,at.Y-Directions[inDir].Y),at)!=null)
                return Distance(at,next);
            lock(stepLengthCache)
            {
                if(stepLengthCache.TryGetValue((inDir,outDir),out double cached))return cached;
                double length=TileLaneLength(inDir,outDir,true);
                stepLengthCache[(inDir,outDir)]=length;return length;
            }
        }
        static Point[] Cubic(Point a,Point b,Point c,Point d,int count)
        {
            var values=new Point[count+1];
            for(int i=0;i<=count;i++){double t=i/(double)count,u=1-t;values[i]=a*(u*u*u)+b*(3*u*u*t)+c*(3*u*t*t)+d*(t*t*t);}
            return values;
        }

        void SetJourney(Vehicle car,List<Cell> route,bool preserveSpeed=false)
        {
            car.Route=new List<Cell>(route);car.Lanes=MakeLanes(route);car.RouteIndex=0;car.DistanceAlongLane=0;
            car.At=route.Count>0?route[0]:car.At;car.Next=route.Count>1?route[1]:car.At;
            car.Progress=0;car.SegmentEntered=Time;if(!preserveSpeed)car.Speed=0;
            car.LegMarks.Clear();car.ParkingLegAt=-1;car.ParkingLegAttached=false;AppendEntranceLane(car);
            car.RouteVersion=NetworkVersion;RegisterRoute(car,false);UpdateLegs(car);
        }

        // Original VehiclePathfindingProcess after LaneUpdateProcess: in the step after a road change every car on a trip
        // re-paths at once. It keeps the lane it is on and the next two (VehicleModel.NumberOfLanesToCommitTo; AssignPath
        // replaces only path[2..]); here the kept lanes run to the end of their tile, so a corner or motorway pair stays
        // whole. The rest is found from where the kept lanes end, arriving in their direction; erased roads are gone
        // from the graph, so a car with no other way keeps its old lanes (the original's last-resort mothballed lane).
        // The original also re-paths stored return paths at every change; the result only matters when the car sets off
        // home, so it is re-found then (AppendReturnLanes), and at once when an erase touches it (RemoveRoadConnection).
        // On from f25 (decision 111): on the dial-timed replay v21d it costs nothing measurable (-1.9 +/- 3.2).
        static readonly bool OriginalRepath=true;
        const int OriginalCommittedLanes=3;
        void RefreshJourneyOriginal(Vehicle car)
        {
            if(!car.Moving||car.RouteVersion==NetworkVersion)return;
            car.RouteVersion=NetworkVersion;
            if((car.Stage!=TripStage.Outbound&&car.Stage!=TripStage.Returning)||car.ParkingLegAttached||car.LegMarks.Count>0)return;
            int last=Math.Min(car.Lanes.Count,car.RouteIndex+OriginalCommittedLanes)-1;
            while(last+1<car.Lanes.Count&&car.Lanes[last+1].Tile==car.Lanes[last].Tile)last++;
            int limit=car.Stage==TripStage.Outbound&&car.ParkingLegAt>=0?car.ParkingLegAt:car.Lanes.Count;
            if(last>=limit-1)return;
            var kept=car.Lanes[last];
            if(kept.IsParking||kept.Next==kept.Tile)return;
            Cell goal=car.Stage==TripStage.Outbound?car.DestinationAccess:Buildings[car.HomeId].Access;
            var route=FindRoute(kept.Next,goal,true,kept.Outgoing);
            if(route.Count<1||route[0]!=kept.Next)return;
            var full=new List<Cell>{kept.Tile};full.AddRange(route);
            var tail=MakeLanes(full).SkipWhile(l=>l.Tile==kept.Tile).ToList();
            if(tail.Count==0)return;
            var oldTail=car.Lanes.Skip(last+1).Take(limit-last-1).Select(l=>l.Key);
            if(oldTail.SequenceEqual(tail.Select(l=>l.Key)))return;
            car.Lanes=car.Lanes.Take(last+1).Concat(tail).ToList();
            var cells=new List<Cell>();foreach(var l in car.Lanes.Skip(car.RouteIndex))if(cells.Count==0||cells[cells.Count-1]!=l.Tile)cells.Add(l.Tile);
            if(cells.Count==0||cells[cells.Count-1]!=goal)cells.Add(goal);car.Route=cells;
            if(car.Stage==TripStage.Outbound){car.ParkingLegAt=-1;AppendEntranceLane(car);}
            RegisterRoute(car,true);UpdateLegs(car);
        }
        void RefreshJourney(Vehicle car)
        {
            if(Rules.Version==GameVersion.OriginalReference&&OriginalRepath){RefreshJourneyOriginal(car);return;}
            if(!car.Moving||car.RouteVersion==NetworkVersion||car.DistanceAlongLane>1e-8||car.CurrentLane.IsJunction||car.CurrentLane.IsRoundabout||car.CurrentLane.IsMotorway||car.CurrentLane.IsParking||car.ParkingLegAttached||car.LegMarks.Count>0||
                (car.Stage!=TripStage.Outbound&&car.Stage!=TripStage.Returning))return;
            var old=car.CurrentLane;
            Cell goal=car.Stage==TripStage.Outbound?car.DestinationAccess:Buildings[car.HomeId].Access;
            var route=FindRoute(old.Tile,goal,true,old.Incoming);car.RouteVersion=NetworkVersion;
            if(route.Count<2)return;
            var lanes=MakeLanes(route);var first=lanes[0];
            var tangent=old.Tangent(0);
            var replacement=CreateLane(Cubic(old.Samples[0],old.Samples[0]+tangent*.25,
                first.Samples.Last()-first.Tangent(first.Length)*.25,first.Samples.Last(),12),old.Tile,old.Previous,first.Next,old.Incoming,first.Outgoing);
            replacement.SpeedLimit=first.SpeedLimit;replacement.IsJunction=first.IsJunction;replacement.IsMotorway=first.IsMotorway;replacement.MotorwayId=first.MotorwayId;lanes[0]=replacement;
            car.Route=route;car.Lanes=lanes;car.RouteIndex=0;car.DistanceAlongLane=0;
            if(car.Stage==TripStage.Outbound){car.ParkingLegAt=-1;AppendEntranceLane(car);}
            RegisterRoute(car,true);UpdateLegs(car);
            if(car.Stage==TripStage.Outbound)
            {var back=FindRoute(car.DestinationAccess,Buildings[car.HomeId].Access,true);if(back.Count>1)car.ReturnRoute=back;}
        }

        public List<Cell> PotentialRoute(Cell start,Cell goal)
        {
            // Independent reference-road witness: terrain and parcels only, never the agent's bad road choices.
            var queue=new MinQueue<Cell>();queue.Push(start,0);var distance=new Dictionary<Cell,double>{{start,0}};
            var previous=new Dictionary<Cell,Cell>();var visited=new HashSet<Cell>();
            while(queue.Count>0)
            {
                var c=queue.Pop();if(!visited.Add(c))continue;
                if(c==goal){var route=new List<Cell>{c};while(c!=start){c=previous[c];route.Add(c);}route.Reverse();return route;}
                for(int d=0;d<8;d++)
                {
                    var n=c+Directions[d];if(!InBounds(n)||Blocked[n.X,n.Y]||Roundabouts.Any(r=>r.Center==n))continue;
                    var b=BuildingAt(n);if(b!=null&&n!=goal&&n!=start)continue;
                    if(!ValidParcelLink(c,n))continue;
                    if(d%2==1)
                    {
                        var a=new Cell(c.X,n.Y);var e=new Cell(n.X,c.Y);
                        if(BuildingAt(a)!=null||BuildingAt(e)!=null||Water[c.X,c.Y]||Water[n.X,n.Y])continue;
                    }
                    double cost=distance[c]+Distance(c,n)+(Water[n.X,n.Y]?.1:0);
                    if(!distance.TryGetValue(n,out var old)||cost<old){distance[n]=cost;previous[n]=c;queue.Push(n,cost);}
                }
            }
            return new List<Cell>();
        }

        void ConnectWitness(Cell from,Cell to)
        {
            var route=PotentialRoute(from,to);
            for(int i=0;i<route.Count;i++)
            {
                var c=route[i];if(BuildingAt(c)==null&&Tile(c)==Infrastructure.None){bridgeFrom=i>0?route[i-1]:(Cell?)null;Build(Water[c.X,c.Y]?BuildTool.Bridge:BuildTool.Road,c);bridgeFrom=null;}
                if(i>0)Connect(route[i-1],c);
            }
        }
        public bool BuildReferenceNetwork()
        {
            bool complete=true;
            foreach(var shop in Buildings.Where(b=>!b.IsHouse))
                foreach(var house in Buildings.Where(b=>b.IsHouse&&b.Color==shop.Color))
                {var path=BestPotentialRoute(house.Access,shop);if(path.Count>1)ConnectWitness(house.Access,path[path.Count-1]);if(BestRouteTo(house.Access,shop).Count<2)complete=false;}
            LastAction=complete?"Reference roads built / all costs recorded":"Some reference routes could not be built";return complete;
        }

        public int DisconnectedColorComponents()
        {
            var visited=new HashSet<Cell>();var servedComponents=new List<HashSet<int>>();
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                var first=new Cell(x,y);if(!CanTraverse(first)||visited.Contains(first))continue;
                var queue=new Queue<Cell>();queue.Enqueue(first);visited.Add(first);
                var homes=new HashSet<int>();var shops=new HashSet<int>();
                while(queue.Count>0)
                {
                    var c=queue.Dequeue();var b=AccessBuildingAt(c);
                    if(b!=null)(b.IsHouse?homes:shops).Add(b.Color);
                    for(int d=0;d<8;d++)if((Connections[c.X,c.Y]&(1<<d))!=0)
                    {var n=c+Directions[d];if(CanTraverse(n)&&visited.Add(n))queue.Enqueue(n);}
                }
                homes.IntersectWith(shops);if(homes.Count>0)servedComponents.Add(homes);
            }
            // Physical connectivity only: unused but connected mixed networks are not penalized.
            if(servedComponents.Count<2||servedComponents.SelectMany(v=>v).Distinct().Count()<2)return 0;
            return servedComponents.Count-1;
        }
    }

    // Stable binary heap; equal costs preserve insertion order for repeatable tie breaks.
    sealed class MinQueue<T>
    {
        readonly List<(T value,double cost,long order)> heap=new List<(T,double,long)>();long serial;
        public int Count=>heap.Count;
        bool Before(int a,int b)=>heap[a].cost<heap[b].cost||heap[a].cost==heap[b].cost&&heap[a].order<heap[b].order;
        public void Push(T value,double cost)
        {heap.Add((value,cost,serial++));for(int i=heap.Count-1;i>0;){int parent=(i-1)/2;if(!Before(i,parent))break;(heap[i],heap[parent])=(heap[parent],heap[i]);i=parent;}}
        public T Pop()
        {var value=heap[0].value;heap[0]=heap[heap.Count-1];heap.RemoveAt(heap.Count-1);for(int i=0;i<heap.Count;){int a=2*i+1,b=a+1;if(a>=heap.Count)break;int next=b<heap.Count&&Before(b,a)?b:a;if(!Before(next,i))break;(heap[i],heap[next])=(heap[next],heap[i]);i=next;}return value;}
    }
}
