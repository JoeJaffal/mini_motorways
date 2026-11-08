using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    public sealed class PlanChunk
    {public double Start,Duration,Variation;public bool Ordered;public double[][] Items;}
    public sealed class ScheduledSpawn
    {public double Time,DemandMultiplier;public int Type,Color,Grouping,Preference,Attempts,Order;}
    public sealed class ScheduledSpawnSnapshot
    {public double Time,DemandMultiplier;public int Color,Grouping,Preference,Attempts;}
    public sealed partial class TrafficWorld
    {
        readonly List<ScheduledSpawn> originalPlan=new List<ScheduledSpawn>();
        void InitializeOriginalPlan()
        {
            originalPlan.Clear();int order=0;
            foreach(var chunk in Map.Plan)
            {
                int n=chunk.Items.Length;if(n==0)continue;
                double start=chunk.Start*Rules.SecondsPerDay,duration=chunk.Duration*Rules.SecondsPerDay;
                var randomTimes=new double[n];for(int i=0;i<n;i++)randomTimes[i]=start+random.NextDouble()*duration;
                Array.Sort(randomTimes);var remaining=chunk.Items.ToList();
                for(int i=0;i<n;i++)
                {
                    int index=chunk.Ordered?i:random.Next(remaining.Count);var item=remaining[index];
                    if(!chunk.Ordered)remaining.RemoveAt(index);
                    if((int)item[0]!=0&&(int)item[0]!=1)continue;
                    double midpoint=start+duration*(i+.5)/n;
                    originalPlan.Add(new ScheduledSpawn{Time=midpoint*(1-chunk.Variation)+randomTimes[i]*chunk.Variation,
                        Type=(int)item[0],Color=(int)item[1],Grouping=(int)item[2],DemandMultiplier=item[3],Preference=(int)item[4],Order=order++});
                }
            }
            SortOriginalPlan();
        }
        void SortOriginalPlan()=>originalPlan.Sort((a,b)=>{int time=a.Time.CompareTo(b.Time);return time!=0?time:a.Order.CompareTo(b.Order);});
        void ProcessOriginalPlan()
        {
            // Retry failed events at their new scheduled time; they must not block unrelated due events.
            int due=originalPlan.Count(p=>p.Time<=Time);
            for(int i=0;i<due&&originalPlan.Count>0&&originalPlan[0].Time<=Time;i++)
            {
                var planned=originalPlan[0];originalPlan.RemoveAt(0);
                bool success;
                if(planned.Type==1)
                {
                    var shop=Buildings.FirstOrDefault(b=>!b.IsHouse&&b.Color==planned.Color);
                    success=shop!=null&&TrySpawnHouse(shop);
                }
                else if(planned.Grouping==3)success=ScheduleDestinationUpgrade(planned.Color,planned.DemandMultiplier);
                else
                {
                    success=Buildings.Count(b=>!b.IsHouse)<Rules.MaxShops&&TrySpawnPlannedDestination(planned);
                    if(success)
                    {
                        var destination=Buildings.Last(b=>!b.IsHouse);destination.PlannedDemandMultiplier=planned.DemandMultiplier;
                        if(destination.SpawnTime==Time)InitializeDestinationDemand(destination);
                    }
                }
                if(!success){planned.Attempts++;planned.Time=Time+(planned.Type==1?OriginalGameplayTuning.HouseRetryDelay:20);originalPlan.Add(planned);}
                SortOriginalPlan();
            }
        }
        public bool ScheduleDestinationUpgrade(int color,double demandMultiplier=1)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return Reject("Custom keeps one destination size");
            if(demandMultiplier<=0||double.IsNaN(demandMultiplier)||double.IsInfinity(demandMultiplier))return Reject("Invalid destination demand multiplier");
            var eligible=Buildings.Where(b=>!b.IsHouse&&!b.IsStation&&!b.Upgraded&&double.IsPositiveInfinity(b.UpgradeAt)&&
                (color<0||b.Color==color)&&SupportsCircle(b)).ToList();
            if(eligible.Count==0)return Reject("No eligible destination for this scheduled upgrade");
            double total=eligible.Sum(b=>Math.Max(0,Time-b.SpawnTime)),pick=random.NextDouble()*total;
            var chosen=eligible[eligible.Count-1];
            foreach(var b in eligible){pick-=Math.Max(0,Time-b.SpawnTime);if(pick<0){chosen=b;break;}}
            chosen.UpgradeAt=Math.Max(Time,chosen.SpawnTime+10);chosen.PlannedDemandMultiplier=demandMultiplier;
            LastAction="Destination "+chosen.Id+" scheduled to upgrade";UpdateDestinationUpgrades();return true;
        }
        bool SupportsCircle(Building shop)
        {
            // EmptyLab deliberately permits controlled mechanism tests away from city placement masks.
            if(!CityCatalog.Maps.Contains(Scenario))return true;
            var zone=Map.CircleZones[shop.Color];
            for(int y=shop.Cell.Y;y<shop.Cell.Y+shop.Height;y++)for(int x=shop.Cell.X;x<shop.Cell.X+shop.Width;x++)
                if(Array.IndexOf(zone,y*Width+x)>=0)return true;
            return false;
        }
        void UpdateDestinationUpgrades()
        {
            if(Rules.Version!=GameVersion.OriginalReference)return;
            foreach(var b in Buildings.Where(b=>!b.IsHouse&&!b.Upgraded&&b.UpgradeAt<=Time))
            {b.Upgraded=true;LastAction="Destination "+b.Id+" upgraded";}
        }
        public int DestinationCapacity(Building shop)=>Rules.DemandCapacity+(shop.IsStation?1:shop.Upgraded?3:0);
        public Point LayoutPoint(Building shop,double x,double y)
        {
            bool flip=shop.SharedLot&&(shop.Layout==1||shop.Layout==3);
            return shop.Layout>=2?new Point(shop.Cell.X+(flip?y:3-y),shop.Cell.Y+x):new Point(shop.Cell.X+x,shop.Cell.Y+(flip?3-y:y));
        }
    }
}
