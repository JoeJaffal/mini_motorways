using System;
using System.Collections.Generic;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        double trafficSurgeTime;
        double trafficSurgeLoad;
        Building trafficSurgeShop;

        void UpdateTrafficPracticeDemand()
        {
            if (CustomScenarioId!=ConstructionCurriculumId || trafficSurgeShop==null || ConstructionExercise==null ||
                !ConstructionExercise.EndsWith("-live",StringComparison.Ordinal) || Time<trafficSurgeTime)
                return;
            trafficSurgeShop.PlannedDemandMultiplier=trafficSurgeLoad;
            trafficSurgeShop.DemandCountdown=Math.Min(trafficSurgeShop.DemandCountdown,.5);
            trafficSurgeShop=null;
        }

        void LoadTrafficPractice(int seed, string split, string exercise)
        {
            if (split != "train" && split != "validation")
                throw new ArgumentException("Unknown traffic practice split");
            Reset(seed, ScenarioKind.EmptyLab);
            trafficSurgeShop=null;
            CustomScenarioId = ConstructionCurriculumId;
            ConstructionExercise = exercise;
            ConstructionReference.Clear();
            var rng = new Random(seed);
            var origin = new Cell(split == "train" ? rng.Next(5,15) : rng.Next(27,35), rng.Next(5,15));
            bool reflect = rng.Next(2)==0;
            Cell At(int x,int y) => new Cell(origin.X+x, origin.Y+(reflect ? 11-y : y));
            var clear = new HashSet<Cell>();
            void Clear(Cell cell) => clear.Add(cell);
            void Path(string gapKind,int missing, params (int x,int y)[] nodes)
            {
                for (int i=0;i<nodes.Length;i++) Clear(At(nodes[i].x,nodes[i].y));
                for (int i=0;i<nodes.Length-1;i++)
                {
                    var a=At(nodes[i].x,nodes[i].y);
                    var b=At(nodes[i+1].x,nodes[i+1].y);
                    if (i==missing) ConstructionReference.Add((gapKind,a,b));
                    else if (!DrawRoad(a,b)) throw new InvalidOperationException("Traffic practice road placement failed");
                }
            }
            Building Shop(int row,int color,double load,int pins)
            {
                var entry=At(10,row);
                // Layout 0 faces west from the parcel's third row.
                var originCell=new Cell(entry.X,entry.Y-2);
                var shop=SpawnBuilding(originCell,color,false,0,0);
                if (shop==null) throw new InvalidOperationException("Traffic practice shop placement failed");
                for (int y=originCell.Y;y<originCell.Y+shop.Height;y++)
                    for (int x=originCell.X;x<originCell.X+shop.Width;x++) Clear(new Cell(x,y));
                shop.PlannedDemandMultiplier=load;
                shop.Demand=pins;
                return shop;
            }
            void Home(int x,int y,int ax,int ay,int color)
            {
                var cell=At(x,y);var approach=At(ax,ay);
                if (SpawnBuilding(cell,color,true,Direction(cell,approach))==null)
                    throw new InvalidOperationException("Traffic practice home placement failed");
                Clear(cell);Clear(approach);
            }
            int c0=rng.Next(3);
            int c1=(c0+rng.Next(1,3))%3;
            bool establishedPriority=exercise=="traffic-priority-established" || exercise=="traffic-priority-established-swap";
            bool priority=establishedPriority || exercise=="traffic-priority"||exercise=="traffic-priority-swap";
            var parts=exercise.Split('-');
            bool high=parts.Length>2 && parts[2]=="high";
            string profile=parts.Length>3 ? parts[3] : "standard";
            bool live=profile=="live";
            bool shortBypass=live||profile=="stockshort"||profile=="stockrush";
            bool economy=profile.StartsWith("stock",StringComparison.Ordinal)||live;
            double highLoad=profile=="stockrush" ? 4.4 : 3.4;
            if (!priority && (parts.Length<3 || parts[1]!="junction" || (parts[2]!="low" && !high)))
                throw new ArgumentException("Unknown traffic practice exercise");
            bool upperBusy=rng.Next(2)==0;
            if (exercise.EndsWith("-swap",StringComparison.Ordinal)) upperBusy=!upperBusy;
            var aShop=Shop(priority ? 3 : 5,c0,priority ? (upperBusy ? 1.65 : .35) : high&&!live ? highLoad : .22,
                           priority ? (upperBusy ? 4 : 0) : high&&!live ? 4 : 0);
            var bShop=Shop(priority ? 9 : 8,c1,priority ? (upperBusy ? .35 : 1.65) : economy ? 2.75 : 2.25,
                           priority ? (upperBusy ? 0 : 4) : 0);
            Array.Clear(Inventory,0,Inventory.Length);
            Inventory[0]=100;
            if (priority)
            {
                if (establishedPriority)
                {
                    // An independent third-color service keeps this a midgame decision.
                    int third=3-c0-c1;
                    Shop(-2,third,.2,0);
                    Home(1,-2,2,-2,third);
                    Path("",-1,(2,-2),(3,-2),(4,-2),(5,-2),(6,-2),(7,-2),(8,-2),(9,-2));
                }
                int upperGap=rng.Next(2,6), lowerGap=rng.Next(2,6);
                foreach (var row in new[] {3,9})
                {
                    int color=row==3 ? c0 : c1;
                    Home(1,row,2,row,color);
                    Home(2,row-1,2,row,color);
                    Home(3,row-1,3,row,color);
                    var lane=new (int x,int y)[8];
                    for (int x=2;x<=9;x++) lane[x-2]=(x,row);
                    Path(row==3 ? "upper" : "lower",row==3 ? upperGap : lowerGap,lane);
                }
            }
            else
            {
                Home(1,5,2,5,c0);
                Home(2,4,2,5,c0);
                Home(3,4,3,5,c0);
                Home(4,4,4,5,c0);
                Home(5,4,5,5,c0);
                Home(6,4,6,5,c0);
                Home(1,8,2,8,c1);
                Home(2,7,2,8,c1);
                if (economy)
                {
                    Home(1,9,0,9,c1);
                    Home(1,10,0,10,c1);
                    Home(1,11,0,11,c1);
                }
                else
                {
                    Home(2,9,2,8,c1);
                    Home(3,7,3,8,c1);
                }
                Path("",-1,(2,5),(3,5),(4,5),(5,5),(6,5),(7,5),(8,5),(9,5));
                Path("",-1,(2,8),(3,8));
                Path("share",live ? -1 : 1,(3,8),(4,7),(4,6),(5,5));
                Path("",-1,(8,5),(9,6),(9,7),(9,8));
                if (economy)
                {
                    Path("feeder",4,(0,11),(0,10),(0,9),(0,8),(1,7),(2,8));
                    if (shortBypass)
                    {
                        Path("separate-entry",live ? -1 : 1,(3,8),(3,9),(4,10),(5,10),(6,10),(7,10));
                        Path("separate-exit",1,(7,10),(8,10),(9,9),(9,8));
                    }
                    else
                    {
                        Path("separate-entry",1,(3,8),(3,9),(3,10),(3,11),(4,11),(5,11),(6,11),(7,11));
                        Path("separate-exit",1,(7,11),(8,11),(9,10),(9,9),(9,8));
                    }
                }
                else if (profile=="standard")
                    Path("separate",1,(3,8),(3,9),(3,10),(3,11),(4,11),(5,11),
                        (6,11),(7,11),(8,11),(9,10),(9,9),(9,8));
                else if (profile=="long")
                    Path("separate",1,(3,8),(3,9),(3,10),(3,11),(4,12),(5,12),
                        (6,12),(7,12),(8,12),(9,11),(9,10),(9,9),(9,8));
                else if (profile=="extra")
                    Path("separate",1,(3,8),(3,9),(3,10),(3,11),(3,12),(4,13),(5,13),
                        (6,13),(7,13),(8,13),(9,12),(9,11),(9,10),(9,9),(9,8));
                else
                    throw new ArgumentException("Unknown bypass profile");
                aShop.DemandCountdown=.1;
                bShop.DemandCountdown=4;
                if (live && high)
                {
                    trafficSurgeShop=aShop;
                    trafficSurgeTime=16+rng.Next(5);
                    trafficSurgeLoad=4.0;
                }
            }
            // Declared building sites and corridors are the available dry land.
            // The normal native legality checker remains responsible for every edit.
            for (int y=0;y<Height;y++) for (int x=0;x<Width;x++)
                if (!clear.Contains(new Cell(x,y))) { Blocked[x,y]=true; Unzoneable[x,y]=true; }
            Inventory[0]=economy&&!live ? 2 : 1;
            ConstructionEditLimit=Inventory[0];
            LastAction="Traffic practice reset";
        }
    }
}
