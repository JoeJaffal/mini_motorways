using System;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Exact acceptance predicates for the deliberately clear-land Stage 1
        // distribution. These do not mutate game state or sample randomness.
        // Do not reuse as a full-city validator: reject unsupported geometry.
        void RequireConnectionPractice(bool constructionCurriculum=false)
        {
            if(CustomScenarioId!=(constructionCurriculum?ConstructionCurriculumId:"connection-practice-v1")||Rules.Version!=GameVersion.OriginalReference||
                Water.Cast<bool>().Any(v=>v)||(!constructionCurriculum&&Blocked.Cast<bool>().Any(v=>v))||Rails.Cast<bool>().Any(v=>v)||
                Motorways.Count!=0||Roundabouts.Count!=0||Signals.Count!=0||Inventory.Skip(1).Any(v=>v!=0))
                throw new InvalidOperationException("Practice legality requires the clear-land Stage 1 distribution");
        }

        bool PracticeRoadCell(Cell cell)=>InBounds(cell)&&IsPlayable(cell)&&BuildingAt(cell)==null&&
            !Blocked[cell.X,cell.Y]&&!PendingRemoval[cell.X,cell.Y]&&Tile(cell)==Infrastructure.None;

        bool PracticeDriveway(Cell house,int direction)
        {
            var outside=house+Directions[direction];
            return InBounds(outside)&&IsPlayable(outside)&&BuildingAt(outside)==null&&
                !PendingRemoval[outside.X,outside.Y];
        }

        bool PracticeParcelLink(Cell from,Cell to,int firstHouseDirection,int secondHouseDirection)
        {
            foreach(var pair in new[]{(from,to,firstHouseDirection),(to,from,secondHouseDirection)})
            {
                var b=BuildingAt(pair.Item1);
                if(b==null)continue;
                int direction=b.IsHouse&&pair.Item3>=0?pair.Item3:AccessDirection(b,pair.Item1);
                if(!HasAccess(b,pair.Item1)||pair.Item2!=pair.Item1+Directions[direction])return false;
            }
            return true;
        }

        bool PracticeDraw(Cell from,Cell to)
        {
            if(!InBounds(from)||!InBounds(to)||from==to||Math.Abs(from.X-to.X)>1||Math.Abs(from.Y-to.Y)>1)return false;
            int direction=Direction(from,to),startDirection=-1,endDirection=-1;
            var start=BuildingAt(from);var end=BuildingAt(to);
            if(start!=null&&start.IsHouse)
            {
                if(!PracticeDriveway(from,direction))return false;
                startDirection=direction;
            }
            // Ordinary DrawRoad can accept creation of a tile even when a later
            // link is refused. Preserve that native behavior; do not require a
            // strategically useful or newly changed connection.
            if(!CanTraverse(from))
                return PracticeRoadCell(from)||(!CanTraverse(to)&&PracticeRoadCell(to));
            bool missing=(Connections[from.X,from.Y]&(1<<direction))==0;
            if(missing&&RoadConnectionCost(from,to)>Inventory[0]&&!retiredConnectionConcrete.ContainsKey(RoadEdge(from,to)))
                return false;
            if(!CanTraverse(to))return PracticeRoadCell(to);
            if(end!=null&&end.IsHouse&&!PracticeParcelLink(from,to,startDirection,-1)&&PracticeDriveway(to,(direction+4)%8))
                endDirection=(direction+4)%8;
            return PracticeParcelLink(from,to,startDirection,endDirection);
        }

        // Exact new-link predicate for paused, no-delete, clear-land practice.
        // An accepted generic draw can merely create a tile and is too broad here.
        public bool[] PracticeNewConnections(bool constructionCurriculum=false)
        {
            RequireConnectionPractice(constructionCurriculum);
            var result=new bool[Width*Height*4];
            if(Failed||ScenarioRejected)return result;
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                var from=new Cell(x,y);
                if(!IsPlayable(from)||(!CanTraverse(from)&&!PracticeRoadCell(from)))continue;
                for(int d=0;d<4;d++)
                {
                    var to=from+Directions[d];
                    if(!InBounds(to)||!IsPlayable(to)||(!CanTraverse(to)&&!PracticeRoadCell(to)))continue;
                    if((Connections[x,y]&(1<<d))!=0||!ValidParcelLink(from,to))continue;
                    if(RoadConnectionCost(from,to)>Inventory[0]&&!retiredConnectionConcrete.ContainsKey(RoadEdge(from,to)))continue;
                    if(d%2==1)
                    {
                        var a=new Cell(from.X,to.Y);var b=new Cell(to.X,from.Y);
                        if((Connections[a.X,a.Y]&(1<<Direction(a,b)))!=0&&
                            !(SplitsCorner(from,to)&&SplitsCorner(a,b)))continue;
                    }
                    result[(y*Width+x)*4+d]=true;
                }
            }
            return result;
        }

        bool PracticeErase(Cell from,Cell to)=>InBounds(from)&&InBounds(to)&&from!=to&&
            Math.Abs(from.X-to.X)<=1&&Math.Abs(from.Y-to.Y)<=1&&
            (Connections[from.X,from.Y]&(1<<Direction(from,to)))!=0;

        public bool[] PracticeDirections(string tool,Cell from)
        {
            RequireConnectionPractice();return PracticeDirectionsUnchecked(tool,from);
        }
        bool[] PracticeDirectionsUnchecked(string tool,Cell from)
        {
            if(tool!="draw"&&tool!="erase")throw new ArgumentException("Unknown practice edge tool");
            var result=new bool[8];
            if(Failed||ScenarioRejected)return result;
            for(int d=0;d<8;d++)result[d]=tool=="draw"?PracticeDraw(from,from+Directions[d]):PracticeErase(from,from+Directions[d]);
            return result;
        }
        public (bool[] draw,bool[] erase,bool[] remove) PracticeSources()
        {
            RequireConnectionPractice();var draw=new bool[Width*Height];var erase=new bool[Width*Height];var remove=new bool[Width*Height];
            if(Failed||ScenarioRejected)return (draw,erase,remove);
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                var c=new Cell(x,y);int k=y*Width+x;
                draw[k]=PracticeDirectionsUnchecked("draw",c).Any(v=>v);
                erase[k]=PracticeDirectionsUnchecked("erase",c).Any(v=>v);
                remove[k]=BuildingAt(c)==null&&Tile(c)!=Infrastructure.None&&!PendingRemoval[x,y];
            }
            return (draw,erase,remove);
        }
    }
}
