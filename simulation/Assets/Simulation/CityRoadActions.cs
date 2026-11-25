using System;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        void RequireCityRoadPilot()
        {
            if(Scenario!=ScenarioKind.LosAngeles||Rules.Version!=GameVersion.OriginalReference||
                Rules.UnlimitedConstruction||CustomScenarioId!=null)
                throw new InvalidOperationException("City road pilot requires the regular Los Angeles scenario");
        }

        bool CityRoadEnd(Cell c)
        {
            if(!InBounds(c)||!IsPlayable(c)||Blocked[c.X,c.Y]||Water[c.X,c.Y]||
                Rails[c.X,c.Y]||PendingRemoval[c.X,c.Y]||RoundaboutAt(c)!=null||
                IsMotorwayEndpoint(c,true))return false;
            var building=BuildingAt(c);
            if(building!=null)return HasAccess(building,c)&&CanTraverse(c);
            return Tile(c)==Infrastructure.None||Tile(c)==Infrastructure.Road;
        }

        bool CanDrawCityRoad(Cell from,Cell to)
        {
            int dx=to.X-from.X,dy=to.Y-from.Y;
            if(Failed||ScenarioRejected||UpgradeChoices.Count>0||from==to||
               Math.Abs(dx)>1||Math.Abs(dy)>1||!CityRoadEnd(from)||!CityRoadEnd(to))return false;
            int d=Direction(from,to);
            if((Connections[from.X,from.Y]&(1<<d))!=0||!ValidParcelLink(from,to)||
                (RoadConnectionCost(from,to)>Inventory[0]&&!retiredConnectionConcrete.ContainsKey(RoadEdge(from,to))))return false;
            if(d%2==0)return true;
            var a=new Cell(from.X,to.Y);
            var b=new Cell(to.X,from.Y);
            return (Connections[a.X,a.Y]&(1<<Direction(a,b)))==0||
                (SplitsCorner(from,to)&&SplitsCorner(a,b));
        }

        public bool[] CityRoadMask()
        {
            RequireCityRoadPilot();
            var mask=new bool[Width*Height*4];
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                var from=new Cell(x,y);
                if(!CityRoadEnd(from))continue;
                for(int d=0;d<4;d++)
                    mask[(y*Width+x)*4+d]=CanDrawCityRoad(from,from+Directions[d]);
            }
            return mask;
        }

        public bool DrawCityRoad(Cell from,Cell to)
        {
            RequireCityRoadPilot();
            if(!CanDrawCityRoad(from,to))return Reject("Choose an available ordinary road connection");
            if(!DrawRoad(from,to)||(Connections[from.X,from.Y]&(1<<Direction(from,to)))==0)
                throw new InvalidOperationException("City road mask disagreed with the native draw");
            return true;
        }

        // The action still requests one undirected neighboring connection.
        // Orient a new crossing from land/existing bridge into empty water,
        // as required by the native stroke rules. No route is selected here.
        void OrientCityConnection(ref Cell from,ref Cell to)
        {
            if(Water[from.X,from.Y]&&OriginalRoadCount(from)==0&&
                !(Water[to.X,to.Y]&&OriginalRoadCount(to)==0))
            {var temporary=from;from=to;to=temporary;}
        }

        bool CityBridgeEnd(Cell c)
        {
            if(!InBounds(c)||!IsPlayable(c)||Blocked[c.X,c.Y]||Rails[c.X,c.Y]||
                PendingRemoval[c.X,c.Y]||RoundaboutAt(c)!=null||IsMotorwayEndpoint(c,true))return false;
            var building=BuildingAt(c);
            if(building!=null)return !Water[c.X,c.Y]&&HasAccess(building,c)&&CanTraverse(c);
            return Tile(c)==Infrastructure.None||
                Tile(c)==(Water[c.X,c.Y]?Infrastructure.Bridge:Infrastructure.Road);
        }

        bool CanDrawCityConnection(Cell from,Cell to)
        {
            if(!InBounds(from)||!InBounds(to))return false;
            if(!Water[from.X,from.Y]&&!Water[to.X,to.Y])return CanDrawCityRoad(from,to);
            if(Failed||ScenarioRejected||UpgradeChoices.Count>0||from==to||
                Math.Abs(from.X-to.X)>1||Math.Abs(from.Y-to.Y)>1||
                !CityBridgeEnd(from)||!CityBridgeEnd(to))return false;
            OrientCityConnection(ref from,ref to);
            int d=Direction(from,to);
            if((Connections[from.X,from.Y]&(1<<d))!=0||!ValidParcelLink(from,to)||
                WaterLinkViolation(from,to)!=null||
                (RoadConnectionCost(from,to)>Inventory[0]&&!retiredConnectionConcrete.ContainsKey(RoadEdge(from,to))))return false;
            if(Water[to.X,to.Y]&&!CanTraverse(to)&&!bridgeSpans.ContainsKey(from)&&Inventory[1]<=0)return false;
            if(d%2==1)
            {
                var a=new Cell(from.X,to.Y);var b=new Cell(to.X,from.Y);
                if((Connections[a.X,a.Y]&(1<<Direction(a,b)))!=0)return false;
            }
            return true;
        }

        public bool[] CityConnectionMask()
        {
            RequireCityRoadPilot();
            var mask=new bool[Width*Height*4];
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                var from=new Cell(x,y);
                if(!CityBridgeEnd(from))continue;
                for(int d=0;d<4;d++)mask[(y*Width+x)*4+d]=CanDrawCityConnection(from,from+Directions[d]);
            }
            return mask;
        }

        public bool DrawCityConnection(Cell from,Cell to)
        {
            RequireCityRoadPilot();
            if(!CanDrawCityConnection(from,to))return Reject("Choose an available road or bridge connection");
            OrientCityConnection(ref from,ref to);
            if(!DrawRoad(from,to)||(Connections[from.X,from.Y]&(1<<Direction(from,to)))==0)
                throw new InvalidOperationException("City connection mask disagreed with the native draw");
            return true;
        }
    }
}
