using System.Linq;
using System.Collections.Generic;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        int connectivityVersion=-1,connectedHouseCount;
        int[] connectedHouseIds=new int[0],suppliedDestinationIds=new int[0];

        // Diagnostic only. Uses current dispatch routing, never potential/future
        // roads or retired links. Each house counts once, regardless of paths.
        public int UsefulConnectedHouseCount()
        {
            if(connectivityVersion==NetworkVersion)return connectedHouseCount;
            var houses=new HashSet<int>();var destinations=new HashSet<int>();
            foreach(var home in Buildings.Where(b=>b.IsHouse&&IsPlayable(b.Cell)))
                foreach(var shop in Buildings.Where(b=>!b.IsHouse&&b.Color==home.Color&&IsPlayable(b.Cell)))
                {
                    var path=BestRouteTo(home.Access,shop);
                    if(path.Count<2||FindRoute(path[path.Count-1],home.Access).Count<2)continue;
                    houses.Add(home.Id);destinations.Add(shop.Id);
                }
            connectivityVersion=NetworkVersion;connectedHouseIds=houses.OrderBy(x=>x).ToArray();
            suppliedDestinationIds=destinations.OrderBy(x=>x).ToArray();connectedHouseCount=houses.Count;
            return connectedHouseCount;
        }
        public object UsefulConnectivityState()
        {UsefulConnectedHouseCount();return new {connectedHouseIds,suppliedDestinationIds};}
    }
}
