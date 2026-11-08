using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly Dictionary<(Cell,Cell,bool),List<Cell>> routeCache=new Dictionary<(Cell,Cell,bool),List<Cell>>();

        public IEnumerable<Cell> Neighbors(Cell at,Cell start,Cell goal)=>Neighbors(at,start,goal,false);
        IEnumerable<Cell> Neighbors(Cell at,Cell start,Cell goal,bool retired)
        {
            if(!InBounds(at))yield break;
            var currentBuilding=BuildingAt(at);
            if(currentBuilding!=null&&at!=start&&at!=goal)yield break;
            var round=RoundaboutAt(at);
            int ringIndex=round==null?-1:Array.IndexOf(round.Ring,at);
            foreach(var m in Motorways.Where(m=>(retired||!m.PendingRemoval)&&(m.Start==at||m.End==at)))
            {var end=m.Other(at);if(CanTraverse(end,retired)&&(retired||!PendingRemoval[at.X,at.Y]))yield return end;}
            for(int d=0;d<8;d++)
            {
                if((Connections[at.X,at.Y]&(1<<d))==0)continue;
                var next=at+Directions[d];
                if(!CanTraverse(next,retired)||!retired&&PendingRemoval[at.X,at.Y])continue;
                var b=BuildingAt(next);if(b!=null&&next!=goal&&next!=start)continue;
                if(ringIndex>=0&&round.Ring.Contains(next)&&next!=round.Ring[(ringIndex+1)%4])continue;
                yield return next;
            }
        }

        public List<Cell> FindRoute(Cell start,Cell goal)=>FindRoute(start,goal,false);
        public List<Cell> FindRoute(Cell start,Cell goal,bool allowRetired)
        {
            if(!InBounds(start)||!InBounds(goal))return new List<Cell>();
            var key=(start,goal,allowRetired);
            if(routeCache.TryGetValue(key,out var cached))return new List<Cell>(cached);
            var origin=(cell:start,dir:8);
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
                    int direction=Direction(state.cell,next);var target=(cell:next,dir:direction);
                    if(closed.Contains(target))continue;
                    var motorway=MotorwayBetween(state.cell,next);
                    double speed=motorway==null?LaneSpeed(state.cell,state.dir,direction):Rules.MotorwaySpeed;
                    double cost=Distance(state.cell,next)/Math.Max(.01,speed);
                    if(state.dir<8&&((direction-state.dir+8)%8)==4)cost+=500;
                    if(allowRetired&&(PendingRemoval[next.X,next.Y]||PendingRemoval[state.cell.X,state.cell.Y]))cost+=100000;
                    double total=costs[state]+Math.Max(1,Math.Floor(10*cost));
                    if(!costs.TryGetValue(target,out var old)||total<old)
                    {costs[target]=total;previous[target]=state;queue.Push(target,total);}
                }
            }
            routeCache[key]=new List<Cell>();return new List<Cell>();
        }

        public double RouteCost(IList<Cell> route)
        {
            if(route.Count<2)return double.PositiveInfinity;double total=0;
            for(int i=0;i<route.Count-1;i++)
            {int incoming=i==0?8:Direction(route[i-1],route[i]);int outgoing=Direction(route[i],route[i+1]);
                double speed=MotorwayBetween(route[i],route[i+1])==null?LaneSpeed(route[i],incoming,outgoing):Rules.MotorwaySpeed;
                total+=Math.Max(1,Math.Floor(10*Distance(route[i],route[i+1])/speed));}
            return total;
        }
        public double LaneSpeed(Cell at,int incoming,int outgoing)
        {
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
                var round=RoundaboutAt(at);
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
                lane.SpeedLimit=LaneSpeed(at,inDir,outDir<8?outDir:0);
                lane.IsJunction=Degree(at)>=3||Tile(at)==Infrastructure.TrafficLight;
                lane.IsRoundabout=round!=null;
                if(motorway!=null){lane.IsMotorway=true;lane.MotorwayId=motorway.Id;lane.IsJunction=false;lane.SpeedLimit=Rules.MotorwaySpeed;lane.Key=$"motorway:{motorway.Id}:{at.X}:{at.Y}";}
                else if(fromMotorway)lane.IsJunction=true;
                // A boundary-based parcel endpoint can coincide with the next lane
                // boundary. Do not create a zero-length lane with an undefined heading.
                if(lane.Distances.Last()<1e-8&&route.Count>1)continue;
                lanes.Add(lane);
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
            car.RouteVersion=NetworkVersion;
        }

        void RefreshJourney(Vehicle car)
        {
            if(!car.Moving||car.RouteVersion==NetworkVersion||car.DistanceAlongLane>1e-8||car.CurrentLane.IsJunction||car.CurrentLane.IsRoundabout||car.CurrentLane.IsMotorway||
                (car.Stage!=TripStage.Outbound&&car.Stage!=TripStage.Returning))return;
            var old=car.CurrentLane;
            Cell goal=car.Stage==TripStage.Outbound?car.DestinationAccess:Buildings[car.HomeId].Access;
            var route=FindRoute(old.Tile,goal,true);car.RouteVersion=NetworkVersion;
            if(route.Count<2)return;
            var lanes=MakeLanes(route);var first=lanes[0];
            var tangent=old.Tangent(0);
            var replacement=CreateLane(Cubic(old.Samples[0],old.Samples[0]+tangent*.25,
                first.Samples.Last()-first.Tangent(first.Length)*.25,first.Samples.Last(),12),old.Tile,old.Previous,first.Next,old.Incoming,first.Outgoing);
            replacement.SpeedLimit=first.SpeedLimit;replacement.IsJunction=first.IsJunction;replacement.IsMotorway=first.IsMotorway;replacement.MotorwayId=first.MotorwayId;lanes[0]=replacement;
            car.Route=route;car.Lanes=lanes;car.RouteIndex=0;car.DistanceAlongLane=0;
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
                var c=route[i];if(BuildingAt(c)==null&&Tile(c)==Infrastructure.None)Build(Water[c.X,c.Y]?BuildTool.Bridge:BuildTool.Road,c);
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
