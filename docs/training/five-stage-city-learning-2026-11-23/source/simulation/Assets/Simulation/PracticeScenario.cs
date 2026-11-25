using System;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Curriculum-only setup. Optional one-gap stage supplies an unfinished road.
        // Native demand, vehicles, scoring, failure and material accounting stay intact.
        public void LoadConnectionPractice(int seed,string split="train",string stage="clear")
        {
            if(split!="train"&&split!="validation")throw new ArgumentException("Unknown practice split");
            if(stage!="clear"&&stage!="one-gap"&&stage!="one-gap-single-build")throw new ArgumentException("Unknown practice stage");
            Reset(seed,ScenarioKind.EmptyLab);
            CustomScenarioId="connection-practice-v1"; // No weekly inventory or scripted city events.
            var rng=new Random(seed);
            // Disjoint destination positions prevent identical layouts crossing splits.
            var origin=new Cell(split=="train"?rng.Next(12,22):rng.Next(30,38),rng.Next(10,19));
            int layout=rng.Next(4),gap=rng.Next(2,6),color=rng.Next(3);
            var shop=SpawnBuilding(origin,color,false,0,layout);
            if(shop==null)throw new InvalidOperationException("Practice destination placement failed");
            var direction=Directions[shop.DrivewayDirection];
            var outside=shop.Access+direction;
            var home=outside;
            for(int i=0;i<gap+1;i++)home+=direction;
            var perpendicular=new Cell(-direction.Y,direction.X);
            int offset=rng.Next(-1,2);
            home=new Cell(home.X+offset*perpendicular.X,home.Y+offset*perpendicular.Y);
            if(SpawnBuilding(home,color,true,rng.Next(8))==null)
                throw new InvalidOperationException("Practice house placement failed");
            Array.Clear(Inventory,0,Inventory.Length);Inventory[0]=20;
            if(stage!="clear")
            {
                // Build the introductory scenario once at reset, never guide policy actions.
                var path=new System.Collections.Generic.List<Cell>{home};
                var at=home;
                while(at!=outside)
                {
                    var next=new Cell(at.X+Math.Sign(outside.X-at.X),at.Y+Math.Sign(outside.Y-at.Y));
                    if(!DrawRoad(at,next))throw new InvalidOperationException("Practice road setup failed");
                    path.Add(next);at=next;
                }
                // Interior edge only: both ends already belong to visible road stubs.
                int missing=rng.Next(1,path.Count-2);
                if(!RemoveRoadConnection(path[missing],path[missing+1]))
                    throw new InvalidOperationException("Practice gap setup failed");
                Array.Clear(Inventory,0,Inventory.Length);Inventory[0]=stage=="one-gap-single-build"?1:20;
            }
            LastAction="Connection practice v1: one house and destination; paused construction";
        }
    }
}
