using System;
using System.Linq;

namespace MotorwaysSim
{
    public static class CityConnectionChecks
    {
        static void Check(bool value,string message)
        {if(!value)throw new InvalidOperationException("CITY CONNECTION CHECK: "+message);}
        static TrafficWorld Fixture()
        {
            var w=new TrafficWorld(99005063,false,Rules.ForVersion(GameVersion.OriginalReference));
            for(int x=17;x<=21;x++)for(int y=16;y<=20;y++)
            {w.Water[x,y]=false;w.Rails[x,y]=false;w.Blocked[x,y]=false;}
            return w;
        }
        static int Slot(Cell a,Cell b)
        {
            int d=TrafficWorld.Direction(a,b);
            if(d>=4){var t=a;a=b;b=t;d=TrafficWorld.Direction(a,b);}
            return (a.Y*TrafficWorld.Width+a.X)*4+d;
        }
        public static int Run()
        {
            int count=0;
            var water=new Cell(19,17);var right=new Cell(20,17);var left=new Cell(18,17);
            {
                var w=Fixture();w.Water[19,17]=true;
                var before=w.Observe();int version=w.NetworkVersion;string message=w.LastAction;
                var legacy=w.CityRoadMask();var mask=w.CityConnectionMask();
                Check(!legacy[Slot(water,right)]&&mask[Slot(water,right)],"new legal bridge edge was hidden by old mask");
                Check(legacy.Select((v,i)=>!v||mask[i]).All(v=>v),"legacy legal edges retained");
                Check(w.NetworkVersion==version&&w.LastAction==message&&before.Inventory.SequenceEqual(w.Inventory)&&
                    before.Connections.SequenceEqual(w.Observe().Connections),"mask is read-only");
                Check(w.DrawCityConnection(water,right),"canonical water-to-land edge is oriented legally");
                Check(w.Inventory[0]==24&&w.Inventory[1]==0,"entry consumes one road and one bridge");
                Check(!w.CityConnectionMask()[Slot(water,right)],"no repeated edge");
                Check(w.DrawCityConnection(left,water)&&w.Inventory[0]==23&&w.Inventory[1]==0,"exit costs road, not another bridge");
                var branch=new Cell(19,18);Check(!w.CityConnectionMask()[Slot(water,branch)],"no bridge intersection");
                var stock=(int[])w.Inventory.Clone();Check(!w.DrawCityConnection(water,branch)&&stock.SequenceEqual(w.Inventory),"rejected edit spends nothing");count++;
            }
            {
                var w=Fixture();w.Water[18,17]=w.Water[19,17]=true;
                Check(!w.CityConnectionMask()[Slot(left,water)],"cannot start in two empty water cells");
                Check(w.DrawCityConnection(water,right),"enter span");
                Check(w.DrawCityConnection(left,water)&&w.Inventory[1]==0,"extend span with no spare bridge");
                Check(w.DrawCityConnection(new Cell(17,17),left)&&w.Inventory[0]==22,"exit extended span");count++;
            }
            {
                var w=Fixture();w.Water[19,17]=true;w.Inventory[1]=0;
                Check(!w.CityConnectionMask()[Slot(water,right)],"no new span without bridge stock");
                w.Inventory[1]=1;w.Inventory[0]=0;
                Check(!w.CityConnectionMask()[Slot(water,right)],"bridge also needs concrete");
                Check(!w.DrawCityConnection(new Cell(-1,0),water)&&w.Inventory[1]==1,"invalid endpoints are rejected");count++;
            }
            {
                var w=Fixture();w.Water[19,17]=true;
                Check(w.DrawCityRoad(new Cell(18,17),new Cell(19,18)),"crossing control road");
                Check(!w.CityConnectionMask()[Slot(new Cell(18,18),water)],"bridge cannot cross a diagonal");
                int stock=w.Inventory[1];Check(!w.DrawCityConnection(new Cell(18,18),water)&&w.Inventory[1]==stock,"crossing rejection has no bridge side effect");count++;
            }
            {
                int transitions=0;
                foreach(int seed in new[]{99005063,99008267,99096723,99265651,99323274,99480639})
                {
                    var a=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.OriginalReference));
                    var b=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.OriginalReference));
                    var rng=new Random(seed);
                    for(int step=0;step<24;step++)
                    {
                        var mask=a.CityConnectionMask();var all=Enumerable.Range(0,mask.Length).Where(i=>mask[i]).ToArray();
                        var bridges=all.Where(i=>{var c=new Cell(i/4%TrafficWorld.Width,i/4/TrafficWorld.Width);var d=c+TrafficWorld.Directions[i%4];return a.Water[c.X,c.Y]||a.Water[d.X,d.Y];}).ToArray();
                        if(all.Length==0)break;var choices=step%3==0&&bridges.Length>0?bridges:all;int slot=choices[rng.Next(choices.Length)];
                        var from=new Cell(slot/4%TrafficWorld.Width,slot/4/TrafficWorld.Width);var to=from+TrafficWorld.Directions[slot%4];
                        Check(a.DrawCityConnection(from,to),"every sampled mask action executes");
                        if(b.Water[from.X,from.Y]&&b.Connections[from.X,from.Y]==0&&!(b.Water[to.X,to.Y]&&b.Connections[to.X,to.Y]==0))
                        {var temp=from;from=to;to=temp;}
                        Check(b.DrawRoad(from,to),"same requested edge through native stroke");
                        Check(a.Inventory.SequenceEqual(b.Inventory)&&a.Observe().Connections.SequenceEqual(b.Observe().Connections)&&
                            a.Observe().Infrastructure.SequenceEqual(b.Observe().Infrastructure)&&a.ConstructionSpent==b.ConstructionSpent&&a.Time==b.Time,
                            "native stroke differential: stock, network, tiles, spending and time");
                        transitions++;
                    }
                }
                Check(transitions==144,"complete differential transition budget");count++;
            }
            return count;
        }
    }
}
