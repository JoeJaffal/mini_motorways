using System;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Conservative local dry-run: false proves no physical network change.
        // True is only "may change", not a route suggestion or legal guarantee.
        public bool DrawMayChange(Cell from,Cell to)
        {
            if(!InBounds(from)||!InBounds(to))return false;
            var cells=RasterLine(from,to);var house=BuildingAt(from);
            if(house!=null&&house.IsHouse&&cells.Count>1)
            {
                int direction=Direction(from,cells[1]);var outside=from+Directions[direction];
                if(!IsPlayable(outside)||Blocked[outside.X,outside.Y]||Water[outside.X,outside.Y]||
                    BuildingAt(outside)!=null||PendingRemoval[outside.X,outside.Y]||Roundabouts.Any(r=>r.Center==outside))return false;
                if(direction!=house.DrivewayDirection)return true;
                bool a=(Connections[from.X,from.Y]&(1<<direction))!=0;
                bool b=(Connections[outside.X,outside.Y]&(1<<((direction+4)%8)))!=0;
                if(CanTraverse(outside)?!a||!b:a||b)return true;
            }
            Cell? previous=null;
            foreach(var c in cells)
            {
                if(!CanTraverse(c))
                {
                    if(IsPlayable(c)&&!Blocked[c.X,c.Y]&&BuildingAt(c)==null&&!PendingRemoval[c.X,c.Y]&&
                        RoundaboutAt(c)==null&&Tile(c)==Infrastructure.None)return true;
                    previous=null;continue;
                }
                if(previous.HasValue)
                {
                    var a=previous.Value;int d=Direction(a,c);
                    if((Connections[a.X,a.Y]&(1<<d))==0&&ValidParcelLink(a,c))
                    {
                        // Rail restrictions may reject this, but admitting it is
                        // conservative; never mutate LastAction with a probe.
                        if(d%2==0)return true;
                        var x=new Cell(a.X,c.Y);var y=new Cell(c.X,a.Y);
                        if((Connections[x.X,x.Y]&(1<<Direction(x,y)))==0)return true;
                    }
                }
                previous=c;
            }
            return false;
        }

        public bool[] DrawChangeChoices(Cell from)
        {
            var result=new bool[Width*Height];
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)result[y*Width+x]=DrawMayChange(from,new Cell(x,y));
            return result;
        }
    }
}
