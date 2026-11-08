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
            // Standard-play motorway spans consume no concrete. Surface roads remain separate stock.
            int number=replacement==null?1:replacement.Number;
            if(replacement==null)while(Motorways.Any(m=>m.Number==number))number++;
            var motorway=new MotorwayState{Id=nextMotorwayId++,Number=number,Start=start,End=end};
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
        public bool IsMotorwayEndpoint(Cell c,bool retired=false)=>Motorways.Any(m=>(retired||!m.PendingRemoval)&&(m.Start==c||m.End==c));
    }
}
