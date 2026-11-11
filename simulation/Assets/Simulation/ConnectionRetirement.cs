using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly Dictionary<(Cell,Cell),int> retiredConnectionConcrete=new Dictionary<(Cell,Cell),int>();
        readonly HashSet<Cell> erasedEndpointCleanup=new HashSet<Cell>();
        public bool RemoveRoadConnection(Cell from,Cell to)
        {
            if(Failed||ScenarioRejected||!InBounds(from)||!InBounds(to)||Distance(from,to)>1.5||from==to)
                return Reject("Choose an existing neighboring road connection");
            int direction=Direction(from,to);
            if((Connections[from.X,from.Y]&(1<<direction))==0)return Reject("No such road connection");
            bool original=Rules.Version==GameVersion.OriginalReference;
            // The original clears an exit into a ring tile like any road link; only the ring's own links need the circle tool.
            if(original?RoundaboutAt(from)!=null&&RoundaboutAt(to)!=null:RoundaboutAt(from)!=null||RoundaboutAt(to)!=null)return Reject("Remove a roundabout with its tool");
            var edge=RoadEdge(from,to);int credit=paidRoadConnections.Remove(edge)?1:0;
            Unlink(from,to);retiredConnectionConcrete[edge]=retiredConnectionConcrete.TryGetValue(edge,out int prior)?prior+credit:credit;
            Changed();
            // Original LaneUpdateProcess: cars that can reach a changed lane are re-pathed, return paths included, so a
            // stored way home that used the erased link moves to an alternative (when one exists) and stops holding it.
            if(original)
                foreach(var car in Cars.Where(c=>c.Stage!=TripStage.Home&&c.Stage!=TripStage.Returning&&c.ShopId>=0&&c.ReturnRoute.Count>1))
                {
                    bool uses=false;for(int i=1;i<car.ReturnRoute.Count&&!uses;i++)uses=RoadEdge(car.ReturnRoute[i-1],car.ReturnRoute[i])==edge;
                    if(!uses)continue;
                    var alternate=FindRoute(car.DestinationAccess,Buildings[car.HomeId].Access,true);
                    if(alternate.Count>1)car.ReturnRoute=alternate;
                }
            FinishConnectionRetirements();LastAction="Road connection retired";return true;
        }
        bool UsesRetiredConnection(Vehicle car,(Cell,Cell) edge)
        {
            if(car.Stage==TripStage.Home)return false;
            if(car.Lanes.Skip(car.RouteIndex).Any(l=>!l.IsParking&&!l.IsMotorway&&
                (RoadEdge(l.Previous,l.Tile)==edge||RoadEdge(l.Tile,l.Next)==edge)))return true;
            if(car.Stage!=TripStage.Returning)
                for(int i=1;i<car.ReturnRoute.Count;i++)if(RoadEdge(car.ReturnRoute[i-1],car.ReturnRoute[i])==edge)return true;
            return false;
        }
        void FinishConnectionRetirements()
        {
            foreach(var item in retiredConnectionConcrete.ToArray())
            {
                if(Cars.Any(c=>UsesRetiredConnection(c,item.Key)))continue;
                Inventory[0]+=item.Value;retiredConnectionConcrete.Remove(item.Key);Changed();
                foreach(var cell in new[]{item.Key.Item1,item.Key.Item2})
                    if(Tile(cell)==Infrastructure.Road&&Degree(cell)==0)
                    {
                        if(IsMotorwayEndpoint(cell,true))erasedEndpointCleanup.Add(cell);
                        else {Tiles[cell.X,cell.Y]=Infrastructure.None;Changed();}
                    }
            }
            foreach(var cell in erasedEndpointCleanup.ToArray())
            {
                if(Degree(cell)>0||Tile(cell)!=Infrastructure.Road){erasedEndpointCleanup.Remove(cell);continue;}
                if(IsMotorwayEndpoint(cell,true))continue;
                Tiles[cell.X,cell.Y]=Infrastructure.None;erasedEndpointCleanup.Remove(cell);Changed();
            }
        }
    }
}
