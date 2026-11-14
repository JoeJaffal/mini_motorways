using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly Dictionary<int,double> lastHouseSpawn=new Dictionary<int,double>();
        readonly Dictionary<int,double> houseRetryAt=new Dictionary<int,double>();
        readonly Dictionary<int,double> delayedSpawnDemand=new Dictionary<int,double>();
        double ExtraDemandFor(int color)=>Rules.Version==GameVersion.OriginalReference&&delayedSpawnDemand.TryGetValue(color,out var value)?value:0;
        void UpdateDelayedSpawnDemand()
        {
            delayedSpawnDemand.Clear();if(Rules.Version!=GameVersion.OriginalReference)return;
            var active=Buildings.Where(b=>!b.IsHouse).GroupBy(b=>b.Color)
                .ToDictionary(g=>g.Key,g=>g.Sum(b=>.800000011920929*(b.Upgraded?2:1)*b.PlannedDemandMultiplier));
            double total=active.Values.Sum();if(total<=0)return;
            int late=originalPlan.Count(p=>p.Attempts>5);double multiplier=late>0?1+Math.Log(late,2):1;
            foreach(var group in originalPlan.Where(p=>p.Type==0&&p.Attempts>0).GroupBy(p=>p.Color))
            {
                double remainder=group.Sum(p=>p.DemandMultiplier*(p.Attempts>5?multiplier:1));
                if(active.TryGetValue(group.Key,out var capacity))
                {
                    double allocated=Math.Min(capacity,remainder);delayedSpawnDemand[group.Key]=
                        ExtraDemandFor(group.Key)+allocated/capacity;remainder-=allocated;
                }
                if(remainder>0)foreach(var color in active.Keys.Where(c=>c!=group.Key))
                    delayedSpawnDemand[color]=ExtraDemandFor(color)+remainder/total;
            }
        }
        public double HouseSupplyContribution(Building house,Building destination)
        {
            int dx=Math.Abs(house.Cell.X-destination.Access.X),dy=Math.Abs(house.Cell.Y-destination.Access.Y);
            double distance=Math.Min(dx,dy)*Math.Sqrt(2)+Math.Abs(dx-dy);
            return ReferenceCurves.Evaluate(OriginalGameplayTuning.HouseContribution,distance)*OriginalGameplayTuning.HouseContributionMultiplier;
        }
        public double RequiredHouseSupply(Building shop)=>shop.IsStation?double.Epsilon:
            Rules.AverageCarsPerDay*DemandRamp*.800000011920929*(shop.Upgraded?2:1)*shop.PlannedDemandMultiplier+ExtraDemandFor(shop.Color);
        public bool HasSufficientHouseSupply(Building shop)
        {
            double supply=Buildings.Where(h=>h.IsHouse&&h.Color==shop.Color).Sum(h=>HouseSupplyContribution(h,shop));
            int count=Buildings.Count(s=>!s.IsHouse&&!s.IsStation&&s.Color==shop.Color);
            return supply*(shop.IsStation?1:ReferenceCurves.Evaluate(OriginalGameplayTuning.DestinationSupplyScale,count))>=RequiredHouseSupply(shop);
        }
        void UpdateOriginalHouseSupply()
        {
            foreach(var group in Buildings.Where(s=>!s.IsHouse).GroupBy(s=>s.Color).ToArray())
            {
                int color=group.Key;
                if(originalPlan.Any(p=>p.Type==1&&p.Color==color))continue;
                if(lastHouseSpawn.TryGetValue(color,out var last)&&Time<last+OriginalGameplayTuning.HouseSpawnDelay||
                    houseRetryAt.TryGetValue(color,out var retry)&&Time<retry)continue;
                var shop=group.FirstOrDefault(s=>!HasSufficientHouseSupply(s));if(shop==null)continue;
                if(!TrySpawnHouse(shop))houseRetryAt[color]=Time+OriginalGameplayTuning.HouseRetryDelay;
            }
        }
        void InitializeDestinationDemand(Building shop)
        {
            shop.DemandCountdown=Time<1?3:OriginalDemandInterval(shop)*DemandRamp;
            shop.NextDemand=Time+shop.DemandCountdown/DemandRamp;
        }
        public Building SpawnBuilding(Cell cell,int color,bool house,int drivewayDirection=0,int layout=0)
        {
            if(color<0||color>=Map.BaseDemand.Length)return null;
            if(layout<0||layout>3)return null;
            int width=house?1:layout>=2?3:2,height=house?1:layout>=2?2:3;
            Cell entrance=house?cell:layout==0?new Cell(cell.X,cell.Y+2):layout==1?new Cell(cell.X+1,cell.Y+2):layout==2?cell:new Cell(cell.X,cell.Y+1);
            int accessDirection=house?drivewayDirection:new[]{4,0,6,2}[layout];
            for(int y=cell.Y;y<cell.Y+height;y++)for(int x=cell.X;x<cell.X+width;x++)
            {var c=new Cell(x,y);if(!InBounds(c)||!IsPlayable(c)||Water[x,y]||Blocked[x,y]||Unzoneable[x,y]||BuildingAt(c)!=null||Tile(c)!=Infrastructure.None||IsMotorwayEndpoint(c,true)||
                Buildings.Any(existing=>Accesses(existing).Any(e=>e+Directions[AccessDirection(existing,e)]==c)))return null;}
            var b=new Building{Id=Buildings.Count,Cell=cell,Entrance=entrance,Layout=house?0:layout,Color=color,IsHouse=house,
                Width=width,Height=height,DrivewayDirection=accessDirection,SpawnTime=Time,
                NextDemand=Time+Rules.FirstDemandDelay,SpawnGraceUntil=Time+Rules.ConstructionGraceSeconds,
                DemandCountdown=Rules.FirstDemandDelay,DemandPhase=Rules.Version==GameVersion.Custom?random.NextDouble()*Map.PeriodDays[color]:0,Parking=house?null:Enumerable.Repeat(-1,Rules.Version==GameVersion.OriginalReference?3:Rules.ParkingSpaces).ToArray()};
            var outside=b.Access+Directions[b.DrivewayDirection];if(!InBounds(outside)||!IsPlayable(outside)||Blocked[outside.X,outside.Y]||Water[outside.X,outside.Y]||BuildingAt(outside)!=null||Roundabouts.Any(r=>r.Center==outside))return null;
            if(!house){b.CarparkId=b.Id;b.Entrances=new[]{b.Entrance};b.EntranceDirections=new[]{b.DrivewayDirection};}
            Buildings.Add(b);
            if(house)lastHouseSpawn[color]=Time;
            else if(Rules.Version==GameVersion.OriginalReference)
            {
                InitializeDestinationDemand(b);
            }
            if(house)for(int i=0;i<2;i++)Cars.Add(new Vehicle{Id=Cars.Count,HomeId=b.Id,Color=color,Stage=TripStage.Home,At=cell,Next=cell,ArrivedHome=Time});
            if(CanTraverse(outside))Link(b.Access,outside);
            Changed();
            foreach(var s in Buildings.Where(v=>!v.IsHouse))s.LastFeasibilityCheck=-100;
            return b;
        }

        bool TrySpawnShop(int color)
        {
            var candidates=Map.ShopZones[color].Select(k=>new Cell(k%Width,k/Width)).ToList();
            Shuffle(candidates);
            foreach(var candidate in candidates.Take(250))
            {
                // Keep an initial neighborhood compact; expansion of the map itself is deferred.
                if(Rules.Version==GameVersion.Custom&&Time<40&&(candidate.X<10||candidate.X>32||candidate.Y<4||candidate.Y>21))continue;
                Building shop=null;int firstLayout=Rules.Version==GameVersion.OriginalReference?random.Next(4):0;
                for(int l=0;l<(Rules.Version==GameVersion.OriginalReference?4:1)&&shop==null;l++)shop=SpawnBuilding(candidate,color,false,0,(firstLayout+l)%4);
                if(shop==null)continue;
                bool supply=Buildings.Any(b=>b.IsHouse&&b.Color==color&&BestPotentialRoute(b.Access,shop).Count>1);
                if(!supply)supply=TrySpawnHouse(shop);
                if(!supply)
                {DiscardDestination(shop);continue;}
                RefreshFeasibility(shop);
                if(autoConnectReference)BuildReferenceNetwork();
                LastAction=$"New {ColorName(color)} destination / feasible supporting supply available";
                return true;
            }
            return false;
        }

        bool TrySpawnHouse(Building shop)
        {
            var candidates=Map.HouseZones[shop.Color].Select(k=>new Cell(k%Width,k/Width)).ToList();
            Shuffle(candidates);
            // Original spawn regions are preferred. A feasible fallback is our explicitly provisional safeguard.
            if(Rules.Version==GameVersion.Custom)candidates=candidates.OrderBy(c=>Distance(c,shop.Access)<3?100:Math.Abs(Distance(c,shop.Access)-6)).ToList();
            foreach(var candidate in candidates.Take(300))
            {
                if(Rules.Version==GameVersion.Custom&&(Distance(candidate,shop.Access)<3||Distance(candidate,shop.Access)>18))continue;
                int direction=Direction(candidate,shop.Access);
                // A cardinal driveway keeps placement and parcel access unambiguous.
                direction=((direction+1)/2*2)%8;
                var house=SpawnBuilding(candidate,shop.Color,true,direction);if(house==null)continue;
                if(BestPotentialRoute(house.Access,shop).Count>1)
                {if(autoConnectReference)ConnectWitness(house.Access,shop.Access);return true;}
                Cars.RemoveAll(v=>v.HomeId==house.Id);Buildings.Remove(house);Changed();
            }
            return false;
        }

        static void Swap<T>(IList<T> values,int a,int b){T temp=values[a];values[a]=values[b];values[b]=temp;}
        void Shuffle<T>(IList<T> values){for(int i=values.Count-1;i>0;i--)Swap(values,i,random.Next(i+1));}
        public static string ColorName(int color)=>new[]{"red","blue","green","yellow","purple","orange"}[Math.Max(0,Math.Min(5,color))];

        void UpdateCity()
        {
            if(!Rules.EnableCityGrowth||!CityCatalog.Maps.Contains(Scenario))return;
            if(Rules.Version==GameVersion.OriginalReference){ProcessOriginalPlan();UpdateOriginalHouseSupply();return;}
            else if(nextScheduledShop<spawnSchedule.Count&&Time>=spawnSchedule[nextScheduledShop].time)
            {
                int color=spawnSchedule[nextScheduledShop].color;
                if(Buildings.Count(b=>!b.IsHouse)<Rules.MaxShops&&TrySpawnShop(color))nextScheduledShop++;
                else {var item=spawnSchedule[nextScheduledShop];spawnSchedule[nextScheduledShop]=(Time+20,item.color);}
            }
            if(Time<NextSpawn)return;
            NextSpawn=Time+Rules.HouseSpawnInterval;
            // Place supporting houses by the weakest original demand/supply ratio, not the agent's road layout.
            var shops=Buildings.Where(b=>!b.IsHouse).OrderByDescending(b=>b.FeasibleDemandInterval).ToList();
            foreach(var shop in shops)
            {
                int homes=Buildings.Count(b=>b.IsHouse&&b.Color==shop.Color),destinations=Buildings.Count(b=>!b.IsHouse&&b.Color==shop.Color);
                if(homes>=destinations*5)continue;
                if(TrySpawnHouse(shop)){LastAction=$"New {ColorName(shop.Color)} house / two reusable cars";break;}
            }
        }

        void RefreshFeasibility(Building shop)
        {
            shop.LastFeasibilityCheck=Time;double capacity=0;List<Cell> witness=null;
            foreach(var house in Buildings.Where(h=>h.IsHouse&&h.Color==shop.Color))
            {
                var routes=new List<(Building shop,List<Cell> path,double distance)>();
                foreach(var other in Buildings.Where(s=>!s.IsHouse&&s.Color==shop.Color))
                {
                    var path=BestPotentialRoute(house.Access,other);if(path.Count<2)continue;
                    double distance=0;for(int i=1;i<path.Count;i++)distance+=Distance(path[i-1],path[i]);
                    routes.Add((other,path,distance));
                }
                var target=routes.FirstOrDefault(v=>v.shop==shop);if(target.path==null)continue;
                double totalWeight=routes.Sum(v=>1/Math.Max(1,v.distance));
                double share=(1/Math.Max(1,target.distance))/Math.Max(.0001,totalWeight);
                // Includes turnaround, parking, acceleration, and a conservative occupancy margin.
                double cycle=target.distance*2/(Rules.CarSpeed*Rules.RightAngleMultiplier)+Rules.ServiceSeconds+8;
                capacity+=2/cycle*share;
                if(witness==null||target.path.Count<witness.Count)witness=target.path;
            }
            shop.FeasibilityVerified=capacity>0;
            shop.FeasibleDemandInterval=capacity>0?1/(capacity*Rules.CapacitySafetyFactor):double.PositiveInfinity;
            shop.FeasibilityRoute=witness??new List<Cell>();
        }

        bool ClearlyInsufficientSupply(Building shop)
        {
            // Reject only if even an optimistic bound is insufficient. The conservative
            // service estimate is diagnostic, not evidence of impossibility.
            if(Time-shop.SupplyBoundCheckedAt<20&&shop.SupplyBoundBuildingCount==Buildings.Count)
                return shop.MaximumPotentialArrivalRate+1e-9<1/Math.Max(.001,shop.OriginalDemandInterval);
            double capacity=0;double maximumSpeed=Rules.CarSpeed*Math.Max(1,Rules.RoundaboutMultiplier);
            var homes=Buildings.Where(h=>h.IsHouse&&h.Color==shop.Color).ToList();
            foreach(var home in homes)
            {
                double shortest=Math.Max(.01,Distance(home.Access,shop.Access)-3);
                capacity+=2*maximumSpeed/(2*shortest);
            }
            if(Rules.EnableCityGrowth&&CityCatalog.Maps.Contains(Scenario))
            {
                // Do not reject a growing city just because supply has not appeared yet.
                // Generously allow remaining ordinary spawn slots at the best zone distance.
                int slots=5*Buildings.Count(b=>!b.IsHouse&&b.Color==shop.Color)-homes.Count;
                if(slots>0)
                {
                    double best=Map.HouseZones[shop.Color].Select(k=>new Cell(k%Width,k/Width))
                        .Where(c=>BuildingAt(c)==null&&!Water[c.X,c.Y]&&!Blocked[c.X,c.Y])
                        .Select(c=>Math.Max(.01,Distance(c,shop.Access)-3)).DefaultIfEmpty(double.PositiveInfinity).Min();
                    capacity+=slots*2*maximumSpeed/(2*best);
                }
            }
            shop.MaximumPotentialArrivalRate=capacity;shop.SupplyBoundCheckedAt=Time;shop.SupplyBoundBuildingCount=Buildings.Count;
            return capacity+1e-9<1/Math.Max(.001,shop.OriginalDemandInterval);
        }

        public double OriginalDemandInterval(Building shop)
        {
            int color=shop.Color;
            double phase=shop.DemandPhase;
            if(Rules.Version==GameVersion.OriginalReference)
            {
                if(!demandGroupPhases.TryGetValue(color,out phase)){phase=random.NextDouble()*Map.PeriodDays[color];demandGroupPhases[color]=phase;}
            }
            double days=Time/Rules.SecondsPerDay+phase,period=Map.PeriodDays[color];
            double wave=Math.Pow(Math.Abs(Math.Sin((days%period)*Math.PI/period)),2+Map.Eccentricity[color]);
            double oscillation=Map.BaseDemand[color]+wave*(Map.BurstDemand[color]-Map.BaseDemand[color]);
            double ramp=DemandRamp;
            return Rules.SecondsPerDay/(Rules.AverageCarsPerDay*(Rules.Version==GameVersion.OriginalReference?3435973888/4294967296.0*(shop.Upgraded?2:1)*shop.PlannedDemandMultiplier:Rules.DemandMultiplier)*Math.Max(.01,oscillation)*ramp);
        }

        double DemandRamp=>Rules.Version==GameVersion.OriginalReference?1+(Map.SpawnRamp[0]>0?Math.Max(0,Day-(int)Map.SpawnRamp[0])*Map.SpawnRamp[1]:0):1+Math.Max(0,Day-35)*.013;

        void UpdateDemand()
        {
            UpdateDelayedSpawnDemand();
            foreach(var shop in Buildings.Where(b=>!b.IsHouse))
            {
                if(Time-shop.LastFeasibilityCheck>20)RefreshFeasibility(shop);
                shop.OriginalDemandInterval=OriginalDemandInterval(shop);
                double interval=Rules.EnforceFeasibility?Math.Max(shop.OriginalDemandInterval,shop.FeasibleDemandInterval):shop.OriginalDemandInterval;
                if(!double.IsInfinity(interval)&&double.IsInfinity(shop.NextDemand))shop.NextDemand=Time+Rules.FirstDemandDelay;
                if(shop.IsStation)shop.NextDemand=double.PositiveInfinity;
                else if(Rules.Version==GameVersion.OriginalReference)
                {
                    shop.DemandCountdown-=Rules.TickSeconds*DemandRamp*(1+ExtraDemandFor(shop.Color));
                    if(shop.DemandCountdown<=0)
                    {
                        if(shop.Demand<DestinationCapacity(shop)+DestinationOverflow(shop))shop.Demand++;
                        shop.DemandCountdown=interval*DemandRamp;
                    }
                    shop.NextDemand=Time+shop.DemandCountdown/DemandRamp;
                }
                else if(Time>=shop.NextDemand)
                {
                    if(!double.IsInfinity(interval)&&shop.Demand<DestinationCapacity(shop)+DestinationOverflow(shop))shop.Demand++;
                    shop.NextDemand=Time+interval;
                }
                if(Time<shop.SpawnGraceUntil)continue;
                if(Rules.RejectInfeasibleScenarios&&ClearlyInsufficientSupply(shop))
                {
                    ScenarioRejected=true;RejectionReason=$"Capacity screen rejected {Map.Name}: shop {shop.Id} fails an optimistic supply bound at original demand. No demand was reduced.";
                    LastAction=RejectionReason;return;
                }
                if(shop.Demand>DestinationCapacity(shop))
                {double speed=shop.OvercrowdingSpeed;shop.OvercrowdingSpeed=Math.Min(1,speed+Rules.OvercrowdingAcceleration*Rules.TickSeconds);
                    shop.OvercrowdedFor+=(Rules.Version==GameVersion.OriginalReference?speed:shop.OvercrowdingSpeed)*Rules.TickSeconds*
                        (Rules.Version==GameVersion.OriginalReference?ReferenceCurves.Evaluate(OriginalGameplayTuning.ExtraDemandTimerSpeed,ExtraDemandFor(shop.Color)):1);}
                else
                {shop.OvercrowdingSpeed=0;shop.OvercrowdedFor=Math.Max(0,Math.Min(shop.OvercrowdedFor,Rules.OvercrowdingSeconds-Rules.OvercrowdingGraceSeconds)-Rules.OvercrowdingReturnSpeed*Rules.TickSeconds);}
                if(shop.OvercrowdedFor>Rules.OvercrowdingSeconds)Failed=true;
            }
        }

        void DispatchDemand()
        {
            var ordered=Buildings.Where(s=>!s.IsHouse&&s.Demand>s.Reserved)
                .OrderByDescending(s=>s.Demand-s.Reserved).ThenBy(s=>s.Id).ToList();
            for(int index=0;index<ordered.Count;index++)
            {
                var shop=ordered[index];int remaining=shop.Demand-shop.Reserved;
                int quota=index==ordered.Count-1?remaining:Math.Min(Math.Max(remaining/2,2),remaining);
                for(int attempt=0;attempt<quota;attempt++)
                {
                    Vehicle chosen=null;List<Cell> best=null;double bestCost=double.PositiveInfinity;
                    foreach(var house in Buildings.Where(h=>h.IsHouse&&h.Color==shop.Color))
                    {
                        var vehicle=Cars.FirstOrDefault(v=>v.HomeId==house.Id&&v.Stage==TripStage.Home&&Time-v.ArrivedHome>=Rules.HomeCooldown);
                        if(vehicle==null)continue;
                        var path=BestRouteTo(house.Access,shop);if(path.Count<2)continue;
                        double cost=RouteCost(path);
                        if(cost<bestCost){chosen=vehicle;best=path;bestCost=cost;}
                    }
                    if(chosen==null)break;
                    var home=Buildings[chosen.HomeId];var back=FindRoute(best[best.Count-1],home.Access);
                    if(back.Count<2)break;
                    chosen.DestinationAccess=best[best.Count-1];chosen.ShopId=shop.Id;chosen.Stage=TripStage.Outbound;chosen.ReturnRoute=back;chosen.HasDelivered=false;chosen.DrivingThrough=false;
                    chosen.JourneyStarted=Time;chosen.LastMoved=Time;chosen.ParkingSlot=-1;shop.Reserved++;
                    SetJourney(chosen,best);
                }
            }
        }

        void Deliver(Vehicle car)
        {
            if(car.HasDelivered||car.ShopId<0)return;
            var shop=Buildings[car.ShopId];shop.Demand=Math.Max(0,shop.Demand-1);shop.Reserved=Math.Max(0,shop.Reserved-1);
            shop.Served++;TripsCompleted++;car.HasDelivered=true;
            shop.OvercrowdedFor=Math.Min(shop.OvercrowdedFor,Rules.OvercrowdingSeconds-Rules.OvercrowdingGraceSeconds);
            shop.OvercrowdedFor=Math.Max(0,shop.OvercrowdedFor-Math.Min(Rules.ArrivalTimerReductionMax,shop.OvercrowdedFor*Rules.ArrivalTimerReductionFraction*
                (Rules.Version==GameVersion.OriginalReference?ReferenceCurves.Evaluate(OriginalGameplayTuning.ArrivalReduction,Time):1)));
            shop.OvercrowdingSpeed*=Rules.ArrivalTimerDeceleration;
        }
    }
}
