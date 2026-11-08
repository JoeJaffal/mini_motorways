using System;
using System.Collections.Generic;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Display only: active trips retain geometry after a driveway/link edit.
        // Never reconnect these edges: new trips must use the current network.
        public List<(Cell From,Cell To)> RetiringRoadLinks()
        {
            var links=new List<(Cell From,Cell To)>();
            var seen=new HashSet<(Cell,Cell)>();
            void Include(Cell a,Cell b)
            {
                if(a==b||!InBounds(a)||!InBounds(b)||Math.Abs(a.X-b.X)>1||Math.Abs(a.Y-b.Y)>1)return;
                int direction=Direction(a,b);
                if((Connections[a.X,a.Y]&(1<<direction))!=0||
                   (Connections[b.X,b.Y]&(1<<((direction+4)%8)))!=0)return;
                if(a.CompareTo(b)>0){var swap=a;a=b;b=swap;}
                if(seen.Add((a,b)))links.Add((a,b));
            }
            foreach(var car in Cars)
            {
                if(car.Stage==TripStage.Home)continue;
                for(int i=car.RouteIndex;i<car.Lanes.Count;i++)
                {
                    var lane=car.Lanes[i];
                    if(lane.IsParking||lane.IsMotorway||lane.IsRoundabout)continue;
                    Include(lane.Previous,lane.Tile);Include(lane.Tile,lane.Next);
                }
                if(car.Stage!=TripStage.Returning)for(int i=1;i<car.ReturnRoute.Count;i++)Include(car.ReturnRoute[i-1],car.ReturnRoute[i]);
            }
            return links;
        }
    }
}
