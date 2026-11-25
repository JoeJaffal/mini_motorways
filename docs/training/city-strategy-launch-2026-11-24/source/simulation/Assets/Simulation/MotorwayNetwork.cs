using System;
using System.Linq;
using System.Collections.Generic;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        public MotorwayState MotorwayBetween(Cell a,Cell b,bool allowRetired=true)=>
            Motorways.Where(m=>(allowRetired||!m.PendingRemoval)&&((m.Start==a&&m.End==b)||(m.Start==b&&m.End==a))).OrderBy(m=>m.PendingRemoval).FirstOrDefault();
        public bool AddMotorway(Cell start,Cell end)=>CreateMotorway(start,end,null);
        public bool EditMotorway(int id,Cell start,Cell end)
        {
            var old=Motorways.Find(m=>m.Id==id&&!m.PendingRemoval);
            if(old==null)return Reject("No active motorway with that id");
            if((old.Start==start&&old.End==end)||(old.Start==end&&old.End==start))return true;
            return CreateMotorway(start,end,old);
        }
        bool CreateMotorway(Cell start,Cell end,MotorwayState replacement)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return Reject("Motorways are excluded from Custom");
            if(Failed||ScenarioRejected)return Reject("Episode ended; reset to build");
            if(!IsPlayable(start)||!IsPlayable(end)||Distance(start,end)<2)return Reject("Choose distinct motorway endpoints at least two tiles apart inside the city");
            foreach(var c in new[]{start,end})
                if(Water[c.X,c.Y]||Blocked[c.X,c.Y]||BuildingAt(c)!=null||RoundaboutAt(c)!=null||
                    PendingRemoval[c.X,c.Y]||Tile(c)==Infrastructure.TrafficLight||Motorways.Any(m=>m!=replacement&&(m.Start==c||m.End==c)))
                    return Reject("Motorway endpoints need clear land or ordinary road, away from buildings and other upgrades");
            if(replacement==null&&Inventory[2]<=0)return Reject("No motorways remaining");
            if(!ChooseRampDirections(start,end,replacement,out int startDirection,out int endDirection))return Reject("No free ramp direction on a motorway end tile");
            // Standard-play motorway spans consume no concrete. Surface roads remain separate stock.
            int number=replacement==null?1:replacement.Number;
            if(replacement==null)while(Motorways.Any(m=>m.Number==number))number++;
            var motorway=new MotorwayState{Id=nextMotorwayId++,Number=number,Start=start,End=end,StartDirection=startDirection,EndDirection=endDirection};
            if(replacement==null)Inventory[2]--;
            else {replacement.PendingRemoval=true;replacement.RefundOnRemoval=false;}
            Motorways.Add(motorway);
            foreach(var endpoint in new[]{start,end})AttachNativeDrivewaysAt(endpoint);
            Changed();FinishMotorwayRemovals();
            Record(BuildTool.Motorway,start,0,"Built motorway "+number+"; connect surface roads to both endpoints");return true;
        }
        public bool RemoveMotorway(int id)
        {
            var m=Motorways.Find(v=>v.Id==id);
            if(m==null||m.PendingRemoval)return Reject("No active motorway with that id");
            if(Failed||ScenarioRejected)return Reject("Episode ended; reset to edit");
            m.PendingRemoval=true;Changed();Record(BuildTool.Remove,m.Start,0,"Motorway retired; committed traffic clears before release");
            FinishMotorwayRemovals();return true;
        }
        static bool RouteUsesMotorway(IList<Cell> route,MotorwayState m)
        {
            for(int i=1;i<route.Count;i++)if((route[i-1]==m.Start&&route[i]==m.End)||(route[i-1]==m.End&&route[i]==m.Start))return true;
            return false;
        }
        void FinishMotorwayRemovals()
        {
            foreach(var m in Motorways.Where(m=>m.PendingRemoval).ToArray())
            {
                bool used=Cars.Any(c=>c.Stage!=TripStage.Home&&
                    (c.Lanes.Skip(c.RouteIndex).Any(l=>l.MotorwayId==m.Id)||c.Stage!=TripStage.Returning&&RouteUsesMotorway(c.ReturnRoute,m)));
                if(used)continue;Motorways.Remove(m);if(m.RefundOnRemoval)Inventory[2]++;Changed();
            }
        }
        // Original AddMotorwayAction.SetDanglingTile: each end's ramp takes one of the tile's eight directions that holds
        // no road (or other ramp). Every pair of free directions is scored by how well the start ramp points along the
        // motorway and the end ramp points back, (a·n/2+1/2)(b·(−n)/2+1/2), plus 0.1 when both lie on the same side of
        // the line; the best pair wins, ties to the first in the original's order (N, NE, E, SE, S, SW, W, NW). When an
        // edit keeps one end, that end keeps its ramp if it still points within 45° of the motorway. The ramp
        // direction is fixed for the motorway's life and blocks road links on that side of the tile.
        static readonly int[] OriginalDirectionOrder={6,7,0,1,2,3,4,5};
        int RampDirection(MotorwayState m,Cell c)=>c==m.Start&&m.StartDirection>=0?m.StartDirection:c==m.End&&m.EndDirection>=0?m.EndDirection:ClosestDirection(c,m.Other(c));
        bool RampBlocks(Cell c,int direction,MotorwayState ignore=null)=>Rules.Version==GameVersion.OriginalReference&&
            Motorways.Any(m=>m!=ignore&&(m.Start==c||m.End==c)&&RampDirection(m,c)==direction);
        bool ChooseRampDirections(Cell start,Cell end,MotorwayState replacement,out int startDirection,out int endDirection)
        {
            startDirection=endDirection=-1;
            var startFree=OriginalDirectionOrder.Where(d=>(Connections[start.X,start.Y]&(1<<d))==0&&!RampBlocks(start,d,replacement)).ToList();
            var endFree=OriginalDirectionOrder.Where(d=>(Connections[end.X,end.Y]&(1<<d))==0&&!RampBlocks(end,d,replacement)).ToList();
            if(startFree.Count==0||endFree.Count==0)return false;
            var n=new Point(end.X-start.X,end.Y-start.Y).Unit;var tangent=new Point(-n.Y,n.X);
            if(replacement!=null)
                foreach(var kept in new[]{start,end})
                {
                    if(kept!=replacement.Start&&kept!=replacement.End)continue;
                    int previous=RampDirection(replacement,kept);var toward=kept==start?n:n*-1;
                    int closest=ClosestDirection(kept,kept==start?end:start);int gap=Math.Abs(previous-closest);gap=Math.Min(gap,8-gap);
                    int preferred=gap<=1&&Point.Dot(DirectionVector(previous),toward)>Math.Cos(Math.PI/4)+1e-9?previous:closest;
                    var free=kept==start?startFree:endFree;
                    if(gap<=1&&free.Contains(preferred)){free.Clear();free.Add(preferred);}
                }
            double best=double.NegativeInfinity;
            foreach(int a in startFree)foreach(int b in endFree)
            {
                var va=DirectionVector(a);var vb=DirectionVector(b);
                double score=(Point.Dot(va,n)*.5+.5)*(Point.Dot(vb,n*-1)*.5+.5);
                if(Point.Dot(va,tangent)*Point.Dot(vb,tangent)>0)score+=.1;
                if(score>best+1e-9){best=score;startDirection=a;endDirection=b;}
            }
            return true;
        }
        public bool IsMotorwayEndpoint(Cell c,bool retired=false)=>Motorways.Any(m=>(retired||!m.PendingRemoval)&&(m.Start==c||m.End==c));
    }
}
