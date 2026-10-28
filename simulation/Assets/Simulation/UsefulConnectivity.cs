using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        int connectivityVersion=-1,connectedHouseCount;

        // Diagnostic only. Uses current dispatch routing, never potential/future
        // roads or retired links. Each house counts once, regardless of paths.
        public int UsefulConnectedHouseCount()
        {
            if(connectivityVersion==NetworkVersion)return connectedHouseCount;
            int count=0;
            foreach(var home in Buildings.Where(b=>b.IsHouse&&IsPlayable(b.Cell)))
                foreach(var shop in Buildings.Where(b=>!b.IsHouse&&b.Color==home.Color&&IsPlayable(b.Cell)))
                {
                    var path=BestRouteTo(home.Access,shop);
                    if(path.Count<2||FindRoute(path[path.Count-1],home.Access).Count<2)continue;
                    count++;break;
                }
            connectivityVersion=NetworkVersion;connectedHouseCount=count;
            return count;
        }
    }
}
