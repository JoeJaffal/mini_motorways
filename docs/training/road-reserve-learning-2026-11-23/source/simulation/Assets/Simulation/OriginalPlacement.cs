using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference free-play building placement, written from our reading of the original's building placer
    // and spawning process (decisions 085-088). Per spawn: a weight per tile from the colour's exported layer, scaled
    // by nearby buildings (4-neighbour distances that do not cross water, mountains or rail), blurred around houses by
    // the density map and cleared around buildings and roundabouts; every legal (tile, layout) placement draws
    // uniform(0, average footprint weight); the highest draw whose driveways can reach open ground wins.
    public sealed partial class TrafficWorld
    {
        public enum PlacementKind {House,Destination,DoubleDestination,Station}
        const int GroupingNormal=0,GroupingNear=1,GroupingFar=2;
        const int HouseGroupingRadius=7,DestinationGroupingRadius=12,DestinationDeadzoneRadius=5,SuburbRadius=5;
        const double PushVeryStrong=.425,PushStrong=.6,PushWeak=.9,Pull=1.3,PullDecreasePerNeighbour=.035,PullMinimum=1.05;
        const int MaxFailedSpawnsBeforeIgnoringWeights=5,MaxFailedDoubleSpawnsBeforeSolo=4;
        const double MinimumTimeBetweenDestinationSpawns=10,FailedDestinationRetryDelay=20;
        const double MinimumSuburbScale=.699999988079071,MinimumSuburbExponent=1.2000000476837158,
            MaximumSuburbScale=.4000000059604645,MaximumSuburbExponent=1.399999976158142,MaximumSuburbMultiplier=4;
        const int MinimumAttemptsForSuburbMultiplier=5,MaximumAttemptsForSuburbMultiplier=10;
        readonly Dictionary<int,int> suburbCount=new Dictionary<int,int>();
        int planOrder;
        internal List<ScheduledSpawn> PendingSpawns=>originalPlan;
        internal int[] PlayableTiles{get{UpdatePlayableBounds();return (int[])playableTiles.Clone();}}

        sealed class PlacementLayout {public int Width,Height,Layout;public Cell[] Driveways;public int[] DrivewayDirections;public Cell[] Platforms=new Cell[0];}
        sealed class PlacementCandidate {public Cell Origin;public PlacementLayout Layout;public double Weight;}

        CityPlacementProfile PlacementProfile=>OriginalPlacementData.Get(Scenario);
        public bool UsesOriginalPlacement=>Rules.Version==GameVersion.OriginalReference&&PlacementProfile!=null&&CityCatalog.Maps.Contains(Scenario);

        // Layouts in canvas offsets (y down). Original north = our direction 6, east 0, south 2, west 4.
        static readonly PlacementLayout[] HouseLayouts=new[]{6,0,2,4}.Select(d=>new PlacementLayout{Width=1,Height=1,Driveways=new[]{new Cell(0,0)},DrivewayDirections=new[]{d}}).ToArray();
        // Our single-lot layouts 0-3 equal the original's four single carpark layouts (decision 085).
        static readonly PlacementLayout[] SingleLayouts={
            new PlacementLayout{Width=2,Height=3,Layout=0,Driveways=new[]{new Cell(0,2)},DrivewayDirections=new[]{4}},
            new PlacementLayout{Width=2,Height=3,Layout=1,Driveways=new[]{new Cell(1,2)},DrivewayDirections=new[]{0}},
            new PlacementLayout{Width=3,Height=2,Layout=2,Driveways=new[]{new Cell(0,0)},DrivewayDirections=new[]{6}},
            new PlacementLayout{Width=3,Height=2,Layout=3,Driveways=new[]{new Cell(0,1)},DrivewayDirections=new[]{2}}};
        // Ordinary double lots have two orientations: vertical with the carpark on the west (our shared layout 2) and
        // horizontal with the carpark on the south (our shared layout 0). Stations add the east and north variants.
        static PlacementLayout SharedLayout(int layout,bool station)
        {
            var l=new PlacementLayout{Width=layout<2?4:3,Height=layout<2?3:4,Layout=layout};
            Cell at(int along,int across)=>layout<2?new Cell(along,layout==1?2-across:across):new Cell(layout==3?across:2-across,along);
            l.Driveways=new[]{at(0,2),at(3,2)};l.DrivewayDirections=layout<2?new[]{4,0}:new[]{6,2};
            if(station)l.Platforms=Enumerable.Range(0,4).Select(i=>at(i,0)).ToArray();
            return l;
        }
        static readonly PlacementLayout[] DoubleLayouts={SharedLayout(2,false),SharedLayout(0,false)};
        static readonly PlacementLayout[] StationLayouts={SharedLayout(2,true),SharedLayout(0,true),SharedLayout(3,true),SharedLayout(1,true)};

        // The 2x2 destination building inside its lot (the original measures destination distances from these tiles).
        public IEnumerable<Cell> DestinationCells(Building shop)
        {
            var c=DestinationCenter(shop);int x=(int)Math.Round(c.X)-1,y=(int)Math.Round(c.Y)-1;
            for(int dy=0;dy<2;dy++)for(int dx=0;dx<2;dx++)yield return new Cell(x+dx,y+dy);
        }

        bool FloodBarrier(int x,int y)=>Water[x,y]||Map.Terrain[y][x]=='^'||Rails[x,y];
        int[,] FloodDistances(IEnumerable<Cell> sources)
        {
            var d=new int[Width,Height];for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)d[x,y]=int.MaxValue;
            var queue=new Queue<Cell>();
            foreach(var s in sources)if(InBounds(s)&&d[s.X,s.Y]!=0){d[s.X,s.Y]=0;queue.Enqueue(s);}
            var steps=new[]{new Cell(0,-1),new Cell(1,0),new Cell(0,1),new Cell(-1,0)};
            while(queue.Count>0)
            {
                var c=queue.Dequeue();int next=d[c.X,c.Y]+1;
                foreach(var step in steps)
                {
                    var n=c+step;if(!InBounds(n)||FloodBarrier(n.X,n.Y)||d[n.X,n.Y]<=next)continue;
                    d[n.X,n.Y]=next;queue.Enqueue(n);
                }
            }
            return d;
        }

        // Inclusive placeable rectangle: the playable area inset by one tile on every side (AllowSpawningAtMapEdges is
        // false in classic rules), clipped to the data canvas.
        internal void PlaceableArea(out int x0,out int y0,out int x1,out int y1)
        {
            UpdatePlayableBounds();
            x0=Math.Max(0,playableTiles[0]+1);x1=Math.Min(Width-1,playableTiles[2]-1);
            y0=Math.Max(0,playableTiles[1]+1);y1=Math.Min(Height-1,playableTiles[3]-1);
        }

        static double LayerWeight(string[] rows,int x,int y){char c=rows[y][x];return c=='.'?-1:(c-'0')/4.0;}

        // Returns the weight grid (negative = forbidden) and the driveway-target grid for one placement.
        void PlacementWeights(int color,PlacementKind kind,int grouping,bool relaxed,out double[,] weight,out bool[,] driveable,
            out int x0,out int y0,out int x1,out int y1)
        {
            var profile=PlacementProfile;bool house=kind==PlacementKind.House;
            string[] layer=kind==PlacementKind.Station?profile.StationWeights:house?profile.HouseWeights[color]:profile.DestinationWeights[color];
            PlaceableArea(out x0,out y0,out x1,out y1);
            weight=new double[Width,Height];driveable=new bool[Width,Height];
            var occupied=new bool[Width,Height];var drivewayTarget=new bool[Width,Height];
            foreach(var b in Buildings)
            {
                for(int y=b.Cell.Y;y<b.Cell.Y+b.Height;y++)for(int x=b.Cell.X;x<b.Cell.X+b.Width;x++)if(InBounds(new Cell(x,y)))occupied[x,y]=true;
                foreach(var e in Accesses(b)){var t=e+Directions[AccessDirection(b,e)];if(InBounds(t))drivewayTarget[t.X,t.Y]=true;}
            }
            var houses=Buildings.Where(b=>b.IsHouse).ToList();var destinations=Buildings.Where(b=>!b.IsHouse).ToList();
            var demandAll=FloodDistances(destinations.SelectMany(DestinationCells));
            var demandOwn=FloodDistances(destinations.Where(b=>b.Color==color).SelectMany(DestinationCells));
            var supplyOwn=FloodDistances(houses.Where(b=>b.Color==color).Select(b=>b.Cell));
            var supplyOther=FloodDistances(houses.Where(b=>b.Color!=color).Select(b=>b.Cell));
            var ownHouses=houses.Where(b=>b.Color==color).Select(b=>b.Cell).ToList();
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                weight[x,y]=-1;
                if(x<x0||x>x1||y<y0||y>y1)continue;
                var c=new Cell(x,y);bool terrain=!Water[x,y]&&!Blocked[x,y];
                driveable[x,y]=terrain&&!occupied[x,y]&&!PendingRemoval[x,y]&&RoundaboutAt(c)==null;
                bool buildable=terrain&&(!Unzoneable[x,y]||Rails[x,y])&&!occupied[x,y]&&Tile(c)==Infrastructure.None&&
                    !drivewayTarget[x,y]&&!PendingRemoval[x,y]&&!IsMotorwayEndpoint(c,true);
                if(!buildable)continue;
                double w=LayerWeight(layer,x,y);
                if(w<0&&relaxed)w=0;
                if(w>0)w=ScaleByBuildingInfluence(w,kind,grouping,demandAll[x,y],demandOwn[x,y],supplyOwn[x,y],supplyOther[x,y],
                    house&&grouping==GroupingNear?ownHouses.Count(h=>(h.X-x)*(h.X-x)+(h.Y-y)*(h.Y-y)<=SuburbRadius*SuburbRadius):0);
                weight[x,y]=w>=0?w:-1;
            }
            var w2=weight;int ax0=x0,ay0=y0,ax1=x1,ay1=y1;
            bool inside(int x,int y)=>x>=ax0&&x<=ax1&&y>=ay0&&y<=ay1;
            void forbid(int left,int top,int width,int height)
            {for(int y=top;y<top+height;y++)for(int x=left;x<left+width;x++)if(inside(x,y))w2[x,y]=-1;}
            // ChangeTileWeightsAroundBuilding: Chebyshev rings 1..radius-1 around a footprint scale by factor^(radius-ring).
            void blur(Building b,int radius)
            {
                for(int ring=1;ring<radius;ring++)
                {
                    double f=Math.Pow(.5,radius-ring);
                    for(int y=b.Cell.Y-ring;y<b.Cell.Y+b.Height+ring;y++)for(int x=b.Cell.X-ring;x<b.Cell.X+b.Width+ring;x++)
                    {
                        if(y!=b.Cell.Y-ring&&y!=b.Cell.Y+b.Height-1+ring&&x!=b.Cell.X-ring&&x!=b.Cell.X+b.Width-1+ring)continue;
                        if(inside(x,y)&&w2[x,y]>=0)w2[x,y]*=f;
                    }
                }
            }
            foreach(var r in Roundabouts)forbid(r.Center.X-1,r.Center.Y-1,3,3);
            foreach(var h in houses)
            {
                blur(h,(profile.Density[h.Cell.Y][h.Cell.X]-'0')*2);
                if(!house)forbid(h.Cell.X-1,h.Cell.Y-1,3,3);
            }
            foreach(var d in destinations)
            {
                if(!house&&d.Color==color)blur(d,DestinationDeadzoneRadius);
                forbid(d.Cell.X-1,d.Cell.Y-1,d.Width+2,d.Height+2);
                // AllowConnectingDriveways is false: a new lot's driveway may not use an existing lot's driveway tile.
                if(!house)foreach(var e in Accesses(d)){var t=e+Directions[AccessDirection(d,e)];if(InBounds(t))driveable[t.X,t.Y]=false;}
            }
        }

        internal static double ScaleByBuildingInfluence(double w,PlacementKind kind,int grouping,int demandAll,int demandOwn,int supplyOwn,int supplyOther,int nearbyOwnHouses)
        {
            if(demandAll<=1||supplyOwn==0||supplyOther==0)return 0;
            if(kind!=PlacementKind.House)
            {
                if(demandOwn>0&&demandOwn<DestinationGroupingRadius)
                {
                    if(grouping==GroupingFar)w*=Math.Pow(PushStrong,DestinationGroupingRadius-demandOwn);
                    else if(grouping==GroupingNear)w*=Math.Pow(Pull,DestinationGroupingRadius-demandOwn);
                }
                // The original's house term for destinations requires 0 < d < 7 and d > 7 at once, so it never applies.
                return w;
            }
            if(supplyOwn>0&&supplyOwn<HouseGroupingRadius)
            {
                if(grouping==GroupingFar)w*=Math.Pow(PushStrong,HouseGroupingRadius-supplyOwn);
                else if(grouping==GroupingNear)
                {
                    double pull=Pull;
                    if(nearbyOwnHouses>0)pull=Math.Max(pull-nearbyOwnHouses*PullDecreasePerNeighbour,PullMinimum);
                    w*=Math.Pow(pull,HouseGroupingRadius-supplyOwn);
                }
            }
            if(demandOwn>0&&demandOwn<HouseGroupingRadius)w*=Math.Pow(PushVeryStrong,HouseGroupingRadius-demandOwn);
            if(supplyOther>0&&supplyOther<HouseGroupingRadius)w*=Math.Pow(PushWeak,(HouseGroupingRadius-supplyOther)*.5);
            return w;
        }

        List<PlacementCandidate> GeneratePlacements(int color,PlacementKind kind,int grouping,bool relaxed)
        {
            PlacementWeights(color,kind,grouping,relaxed,out var weight,out var driveable,out int x0,out int y0,out int x1,out int y1);
            var layouts=kind==PlacementKind.House?HouseLayouts:kind==PlacementKind.Destination?SingleLayouts:kind==PlacementKind.DoubleDestination?DoubleLayouts:StationLayouts;
            var candidates=new List<PlacementCandidate>();
            // The original scans rows from its minimum y (our bottom row) and columns from the left.
            for(int y=y1;y>=y0;y--)for(int x=x0;x<=x1;x++)
            {
                if(weight[x,y]<0)continue;
                foreach(var layout in layouts)
                {
                    if(!AverageFootprintWeight(layout,x,y,weight,x0,y0,x1,y1,out double average))continue;
                    bool ok=true;
                    for(int i=0;i<layout.Driveways.Length&&ok;i++)
                    {
                        var from=new Cell(x+layout.Driveways[i].X,y+layout.Driveways[i].Y);var to=from+Directions[layout.DrivewayDirections[i]];
                        ok=to.X>=x0&&to.X<=x1&&to.Y>=y0&&to.Y<=y1&&driveable[to.X,to.Y]&&!Rails[to.X,to.Y]&&!Rails[from.X,from.Y];
                    }
                    if(ok)candidates.Add(new PlacementCandidate{Origin=new Cell(x,y),Layout=layout,Weight=random.NextDouble()*average});
                }
            }
            return candidates.OrderByDescending(c=>c.Weight).ToList();
        }

        bool AverageFootprintWeight(PlacementLayout layout,int left,int top,double[,] weight,int x0,int y0,int x1,int y1,out double average)
        {
            average=0;int platforms=0;
            for(int dy=0;dy<layout.Height;dy++)for(int dx=0;dx<layout.Width;dx++)
            {
                int x=left+dx,y=top+dy;
                if(x<x0||x>x1||y<y0||y>y1||weight[x,y]<0)return false;
                if(Rails[x,y]){if(Array.IndexOf(layout.Platforms,new Cell(dx,dy))<0)return false;platforms++;}
                average+=weight[x,y];
            }
            average/=layout.Width*layout.Height;
            return platforms==layout.Platforms.Length;
        }

        // BuildingCanFindPathAwayFromDriveway: probe up to eight directions radiating from the driveway; each probe looks
        // five tiles out (up to five more if that tile holds a building) and needs a tile path there that avoids the
        // new footprint; after five probes that reached a free tile without a path, give up.
        bool CanFindPathAwayFromDriveway(Cell start,int direction,HashSet<Cell> footprint)
        {
            int probes=0;
            foreach(int k in new[]{0,1,-1,2,-2,3,-3,4})
            {
                probes++;var step=Directions[((direction+k)%8+8)%8];
                var target=new Cell(start.X+step.X*5,start.Y+step.Y*5);
                for(int i=0;i<5&&!RoadsMayBeDrawn(target);i++)target=target+step;
                if(!RoadsMayBeDrawn(target))continue;
                if(TilePathExists(start,target,footprint))return true;
                if(probes>=5)break;
            }
            return false;
        }
        bool[,] probeOccupied;
        bool RoadsMayBeDrawn(Cell c)=>!InBounds(c)||!probeOccupied[c.X,c.Y];
        // Static terrain: outside the canvas counts as buildable, as the original's matrix default does.
        bool TileBuildable(Cell c)=>!InBounds(c)||PlacementProfile.Unbuildable[c.Y][c.X]!='#';
        bool TilePathExists(Cell start,Cell end,HashSet<Cell> blocked)
        {
            int metro(Cell a){int dx=Math.Abs(a.X-end.X),dy=Math.Abs(a.Y-end.Y),lo=Math.Min(dx,dy);return lo*99+(Math.Max(dx,dy)-lo)*70;}
            var open=new List<(Cell cell,int cost,int total)>{(start,0,metro(start))};var best=new Dictionary<Cell,int>{[start]=metro(start)};
            var closed=new Dictionary<Cell,int>();
            for(int iteration=0;iteration<300&&open.Count>0;iteration++)
            {
                var node=open[0];open.RemoveAt(0);
                if(node.cell==end)return true;
                closed[node.cell]=node.total;
                for(int d=0;d<8;d++)
                {
                    var n=node.cell+Directions[d];
                    if(!TileBuildable(n)||blocked.Contains(n))continue;
                    if(n!=end&&!RoadsMayBeDrawn(n))continue;
                    int cost=node.cost+(d%2==0?70:99),total=cost+metro(n);
                    if(best.TryGetValue(n,out int known)&&total>=known)continue;
                    if(closed.TryGetValue(n,out int done)&&total>=done)continue;
                    open.RemoveAll(o=>o.cell==n);best[n]=total;
                    int at=0;while(at<open.Count&&open[at].total<=total)at++;
                    open.Insert(at,(n,cost,total));
                }
            }
            return open.Count>0&&open[0].cell==end;
        }

        Building ChooseAndSpawn(List<PlacementCandidate> candidates,int color,PlacementKind kind)
        {
            probeOccupied=new bool[Width,Height];
            foreach(var b in Buildings)for(int y=b.Cell.Y;y<b.Cell.Y+b.Height;y++)for(int x=b.Cell.X;x<b.Cell.X+b.Width;x++)if(InBounds(new Cell(x,y)))probeOccupied[x,y]=true;
            foreach(var candidate in candidates)
            {
                var layout=candidate.Layout;var footprint=new HashSet<Cell>();
                for(int dy=0;dy<layout.Height;dy++)for(int dx=0;dx<layout.Width;dx++)footprint.Add(new Cell(candidate.Origin.X+dx,candidate.Origin.Y+dy));
                bool free=true;
                for(int i=0;i<layout.Driveways.Length&&free;i++)
                {
                    var from=candidate.Origin+layout.Driveways[i];
                    free=CanFindPathAwayFromDriveway(from+Directions[layout.DrivewayDirections[i]],layout.DrivewayDirections[i],footprint);
                }
                if(!free)continue;
                Building b=kind==PlacementKind.House?SpawnBuilding(candidate.Origin,color,true,layout.DrivewayDirections[0]):
                    kind==PlacementKind.Destination?SpawnBuilding(candidate.Origin,color,false,0,layout.Layout):
                    SpawnSharedCarpark(candidate.Origin,color,layout.Layout,kind==PlacementKind.Station);
                if(b!=null)return b;
            }
            return null;
        }

        public Building TrySpawnOriginalHouse(int color,int grouping,bool relaxed)
        {
            if(!UsesOriginalPlacement||color<0||color>=PlacementProfile.HouseWeights.Length)return null;
            var house=ChooseAndSpawn(GeneratePlacements(color,PlacementKind.House,grouping,relaxed),color,PlacementKind.House);
            if(house!=null)LastAction=$"New {ColorName(color)} house / two reusable cars";
            return house;
        }

        // AssessGroupingStyleForHouse: a colour's first house is Normal; later houses are Near, becoming a new suburb
        // (Far) with a probability that grows while the suburb count is below the colour's minimum/maximum curves.
        int AssessHouseGrouping(int color)
        {
            if(!suburbCount.TryGetValue(color,out int count)){suburbCount[color]=1;return GroupingNormal;}
            double first=Buildings.Where(b=>!b.IsHouse&&b.Color==color).Select(b=>b.SpawnTime).DefaultIfEmpty(0).Min();
            double days=(Time-first)/Rules.SecondsPerDay;
            int attempts=originalPlan.Where(p=>p.Type==0&&p.Color==color).Select(p=>p.Attempts).DefaultIfEmpty(0).Max();
            attempts=Math.Max(attempts-MinimumAttemptsForSuburbMultiplier,0);
            double scale=1+(MaximumSuburbMultiplier-1)*Math.Min(1,attempts/(double)(MaximumAttemptsForSuburbMultiplier-MinimumAttemptsForSuburbMultiplier));
            var profile=PlacementProfile;
            double minimum=ReferenceCurves.Evaluate(profile.MinimumSuburbs[color],days)*scale,maximum=ReferenceCurves.Evaluate(profile.MaximumSuburbs[color],days)*scale;
            int grouping=GroupingNear;
            if(count<minimum){if(random.NextDouble()<Math.Pow((minimum-count)*MinimumSuburbScale,MinimumSuburbExponent))grouping=GroupingFar;}
            else if(count<maximum){if(random.NextDouble()<Math.Pow((maximum-count)*MaximumSuburbScale,MaximumSuburbExponent))grouping=GroupingFar;}
            if(grouping==GroupingFar)suburbCount[color]=count+1;
            return grouping;
        }

        // ScheduleHouses: a destination whose colour has no pending house and insufficient supply schedules one, no
        // earlier than ten seconds after that colour's latest house (spawned or scheduled).
        void ScheduleOriginalHouses()
        {
            foreach(var shop in Buildings.Where(b=>!b.IsHouse).ToArray())
            {
                int color=shop.Color;
                if(originalPlan.Any(p=>p.Type==1&&p.Color==color)||HasSufficientHouseSupply(shop))continue;
                int grouping=AssessHouseGrouping(color);
                double time=lastHouseSpawn.TryGetValue(color,out var last)?Math.Max(Time,last+OriginalGameplayTuning.HouseSpawnDelay):Time;
                AddPlanned(new ScheduledSpawn{Type=1,Color=color,Grouping=grouping,DemandMultiplier=1,Time=time});
            }
        }
        void AddPlanned(ScheduledSpawn planned)
        {
            planned.Order=planOrder++;originalPlan.Add(planned);SortOriginalPlan();
            if(planned.Type==1&&(!lastHouseSpawn.TryGetValue(planned.Color,out var last)||planned.Time>last))lastHouseSpawn[planned.Color]=planned.Time;
        }

        static bool PrefersDoubleLot(int preference)=>preference==2||preference==3||preference==7||preference==5||preference==8||preference==9;
        static bool StationPreference(int preference)=>preference==5||preference==6||preference==8;

        // SpawnScheduledBuildings for one destination entry (not an upgrade).
        internal bool TrySpawnPlannedDestination(ScheduledSpawn plan)
        {
            if(!UsesOriginalPlacement)return false;
            int color=plan.Color<0?random.Next(Map.BaseDemand.Length):plan.Color;
            // The double-lot roll happens once per entry; its result is kept for retries.
            if(plan.Preference==0){if(random.NextDouble()<=doubleLotProbability){plan.Preference=3;doubleLotProbability=.3;}else{plan.Preference=1;doubleLotProbability+=.05;}}
            int preference=plan.Preference;bool station=StationPreference(preference);
            bool join=preference==2||preference==3||preference==4||preference==5||preference==6;
            if(join)
            {
                // Only the first vacant double lot of the requested kind is considered, and not when it holds this colour.
                var lot=Buildings.FirstOrDefault(b=>b.SharedLot&&b.DestinationSlot==0&&b.IsStation==station&&Buildings.Count(o=>!o.IsHouse&&o.CarparkId==b.CarparkId)==1);
                if(lot!=null&&lot.Color!=color)
                {
                    var joined=JoinSharedCarpark(lot.Id,color);
                    if(joined!=null){joined.PlannedDemandMultiplier=plan.DemandMultiplier;RefreshFeasibility(joined);
                        LastAction=$"New {ColorName(color)} destination joins a double lot";return true;}
                }
            }
            var kind=station?PlacementKind.Station:PrefersDoubleLot(preference)?PlacementKind.DoubleDestination:PlacementKind.Destination;
            var shop=ChooseAndSpawn(GeneratePlacements(color,kind,plan.Grouping,plan.Attempts>MaxFailedSpawnsBeforeIgnoringWeights),color,kind);
            if(shop==null)return false;
            shop.PlannedDemandMultiplier=plan.DemandMultiplier;
            // EnsureMinimumTimeForDestinationSpawnsAfterBuilding: every later destination entry waits at least 10 s.
            foreach(var later in originalPlan)if(later.Type==0&&later.Time<Time+MinimumTimeBetweenDestinationSpawns)later.Time=Time+MinimumTimeBetweenDestinationSpawns;
            SortOriginalPlan();
            RefreshFeasibility(shop);
            LastAction=$"New {ColorName(color)} destination";
            return true;
        }

        int RandomActiveColor()
        {
            var colors=new List<int>();foreach(var b in Buildings)if(!b.IsHouse&&!colors.Contains(b.Color))colors.Add(b.Color);
            return colors.Count==0?0:colors[random.Next(colors.Count)];
        }
    }
}
