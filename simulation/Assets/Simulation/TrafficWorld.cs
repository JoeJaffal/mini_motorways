using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        public const int Width=50,Height=30;
        public readonly Rules Rules;
        public CityProfile Map {get;private set;}
        public MapVariation Variation {get;private set;}
        public bool ScenarioRejected {get;private set;}
        public string RejectionReason {get;private set;}="";
        public int RoadTilesAvailable=>Rules.UnlimitedConstruction?-1:Inventory[0];
        public readonly Infrastructure[,] Tiles=new Infrastructure[Width,Height];
        public readonly bool[,] Water=new bool[Width,Height],Rails=new bool[Width,Height],Blocked=new bool[Width,Height],Unzoneable=new bool[Width,Height];
        public readonly bool[,] PendingRemoval=new bool[Width,Height];
        public readonly int[,] Connections=new int[Width,Height];
        public readonly List<Building> Buildings=new List<Building>();
        public readonly List<Vehicle> Cars=new List<Vehicle>();
        public readonly List<ConstructionEvent> Events=new List<ConstructionEvent>();
        public readonly List<MotorwayState> Motorways=new List<MotorwayState>();
        int nextMotorwayId;
        public readonly List<RoundaboutState> Roundabouts=new List<RoundaboutState>();
        public readonly Dictionary<Cell,SignalState> Signals=new Dictionary<Cell,SignalState>();
        public ScenarioKind Scenario {get;private set;}
        public double Time {get;private set;}
        public int TickCount {get;private set;}
        public int ConstructionSpent {get;private set;}
        public int TripsCompleted {get;private set;}
        public bool Failed {get;private set;}
        public int Seed {get;private set;}
        public string LastAction {get;private set;}="Ready";
        public double NextSpawn {get;private set;}
        public int Day=>(int)(Time/Rules.SecondsPerDay);
        public int Week=>(int)(Time/Rules.SecondsPerWeek)+1;
        public int Hour=>(int)(Time/Rules.SecondsPerDay*24)%24;
        public int DemandTotal=>Buildings.Where(b=>!b.IsHouse).Sum(b=>b.Demand);
        public int ActiveCars=>Cars.Count(c=>c.Stage!=TripStage.Home);
        public int NetworkVersion {get;private set;}
        SimulationRandom random;
        readonly Dictionary<int,double> demandGroupPhases=new Dictionary<int,double>();
        bool autoConnectReference;
        readonly List<(double time,int color)> spawnSchedule=new List<(double,int)>();
        int nextScheduledShop;
        public static readonly Cell[] Directions={new Cell(1,0),new Cell(1,1),new Cell(0,1),new Cell(-1,1),new Cell(-1,0),new Cell(-1,-1),new Cell(0,-1),new Cell(1,-1)};
        public TrafficWorld(int seed=42,bool connected=true,Rules rules=null)
        {Rules=rules??Rules.ForVersion(GameVersion.OriginalReference);Reset(seed,connected?ScenarioKind.ReferenceLab:ScenarioKind.LosAngeles);}
        public bool InBounds(Cell c)=>c.X>=0&&c.Y>=0&&c.X<Width&&c.Y<Height;
        public Infrastructure Tile(Cell c)=>InBounds(c)?Tiles[c.X,c.Y]:Infrastructure.None;
        public Building BuildingAt(Cell c)=>Buildings.Find(b=>b.Contains(c));
        public Building AccessBuildingAt(Cell c)=>Buildings.Find(b=>HasAccess(b,c));
        public RoundaboutState RoundaboutAt(Cell c)=>Roundabouts.Find(r=>r.Center==c||r.Ring.Contains(c));
        public bool IsRoad(Cell c)=>InBounds(c)&&Tile(c)!=Infrastructure.None&&!PendingRemoval[c.X,c.Y];
        public bool CanTraverse(Cell c,bool retired=false)=>InBounds(c)&&(!Blocked[c.X,c.Y])&&
            (AccessBuildingAt(c)!=null||IsMotorwayEndpoint(c,retired)||(Tile(c)!=Infrastructure.None&&(retired||!PendingRemoval[c.X,c.Y])))&&
            !Roundabouts.Any(r=>r.Center==c);
        public static int Direction(Cell a,Cell b)
        {
            int x=Math.Sign(b.X-a.X),y=Math.Sign(b.Y-a.Y);
            for(int i=0;i<8;i++)if(Directions[i].X==x&&Directions[i].Y==y)return i;
            return -1;
        }
        public static double Distance(Cell a,Cell b)=>Point.Distance(new Point(a),new Point(b));
        public void Reset(int seed,bool connected)=>Reset(seed,connected?ScenarioKind.ReferenceLab:ScenarioKind.LosAngeles);
        public void Reset(int seed,ScenarioKind scenario)=>Reset(seed,scenario,MapVariation.SameMap);
        public void Reset(int seed,ScenarioKind scenario,MapVariation variation)
        {
            Variation=variation;
            if(variation==MapVariation.DifferentMaps&&CityCatalog.Maps.Contains(scenario))scenario=CityCatalog.Maps[new Random(seed).Next(CityCatalog.Maps.Length)];
            Map=CityCatalog.Get(scenario);ScenarioRejected=false;RejectionReason="";ResetInventory();
            if(Rules.TickSeconds<=0||Rules.CarsPerHouse!=2)throw new ArgumentException("Positive tick duration and two cars per house are required");
            if(!Rules.UseOriginalIntersectionRules)throw new NotSupportedException("The Lebanese legal alternative remains undecided and is not implemented");
            Seed=seed;Scenario=scenario;random=new SimulationRandom(seed,Rules.Version);Time=0;TickCount=0;ConstructionSpent=0;TripsCompleted=0;Failed=false;
            Buildings.Clear();Cars.Clear();Events.Clear();Roundabouts.Clear();Signals.Clear();Motorways.Clear();nextMotorwayId=0;demandGroupPhases.Clear();spawnSchedule.Clear();nextScheduledShop=0;
            Array.Clear(Tiles,0,Tiles.Length);Array.Clear(Water,0,Water.Length);Array.Clear(Blocked,0,Blocked.Length);
            Array.Clear(Rails,0,Rails.Length);Array.Clear(Unzoneable,0,Unzoneable.Length);Array.Clear(PendingRemoval,0,PendingRemoval.Length);Array.Clear(Connections,0,Connections.Length);
            RailLines.Clear();Trains.Clear();railClosedUntil.Clear();originalPlan.Clear();doubleLotProbability=.3;InitializePlayableArea();
            NetworkVersion++;routeCache.Clear();conflictCache.Clear();
            autoConnectReference=scenario==ScenarioKind.ReferenceLab;
            if(CityCatalog.Maps.Contains(scenario))
            {
                for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
                {
                    char t=Map.Terrain[y][x];
                    Water[x,y]=t=='~';Rails[x,y]=Map.RailLines.Any(line=>line.Cells.Contains(new Cell(x,y)));Blocked[x,y]=t=='#'||t=='^';Unzoneable[x,y]=t==':'||t=='#'||t=='~'||t=='^'||t=='=';
                }
                InitializeRailways();
                if(Rules.Version==GameVersion.OriginalReference){InitializeOriginalPlan();ProcessOriginalPlan();}
                else
                {
                    foreach(var item in Map.ShopSchedule)spawnSchedule.Add((item[0]*20+random.NextDouble()*item[1]*20,(int)item[2]));
                    spawnSchedule.Sort((a,b)=>a.time.CompareTo(b.time));TrySpawnShop(0);if(spawnSchedule.Count>0)nextScheduledShop=1;
                }
                NextSpawn=Rules.HouseSpawnInterval;
                LastAction=Map.Name+" / "+Rules.Version+" / original reference fidelity still under verification";
            }
            else if(scenario==ScenarioKind.ReferenceLab)
            {
                for(int y=0;y<Height;y++)Water[25,y]=true;
                SpawnBuilding(new Cell(10,9),0,true);SpawnBuilding(new Cell(11,19),1,true);SpawnBuilding(new Cell(38,19),2,true);
                SpawnBuilding(new Cell(36,7),0,false);SpawnBuilding(new Cell(35,15),1,false);SpawnBuilding(new Cell(13,7),2,false);
                foreach(var b in Buildings.Where(b=>b.IsHouse).ToArray()) ConnectWitness(b.Access,new Cell(b.Access.X,14));
                foreach(var b in Buildings.Where(b=>!b.IsHouse).ToArray()) ConnectWitness(b.Access,new Cell(b.Access.X,14));
                ConnectWitness(new Cell(10,14),new Cell(38,14));
                Build(BuildTool.TrafficLight,new Cell(36,14));
                // A separate ring example avoids changing a road that already carries trips.
                Build(BuildTool.Roundabout,new Cell(20,14));
                foreach(var b in Buildings.Where(b=>!b.IsHouse))RefreshFeasibility(b);
                NextSpawn=double.PositiveInfinity;
                LastAction=Rules.UnlimitedConstruction?"Connected reference lab / starting construction counts toward spending.":"Material-limited debug lab; reference roads may be incomplete.";
            }
            else {NextSpawn=double.PositiveInfinity;LastAction="Empty road laboratory";}
        }

        public bool Build(BuildTool tool,Cell cell)
        {
            if(!InBounds(cell))return Reject("Outside map");
            if(Failed||ScenarioRejected)return Reject("Episode ended or scenario rejected; reset to build");
            if(!IsPlayable(cell))return Reject("Outside the currently expanded city");
            if(tool==BuildTool.Motorway)return Reject("Choose two motorway endpoints");
            if(BuildingAt(cell)!=null)return Reject("Building parcel; use its driveway");
            if(Blocked[cell.X,cell.Y])return Reject("Unbuildable terrain");
            var old=Tile(cell);
            if(tool==BuildTool.Remove)
            {
                bool removedMotorway=false;
                foreach(var m in Motorways.Where(m=>m.Start==cell||m.End==cell).ToArray())removedMotorway|=RemoveMotorway(m.Id);
                if(old==Infrastructure.None&&removedMotorway)return true;
                var ring=RoundaboutAt(cell);
                if(ring!=null)
                {
                    if(ring.PendingRemoval)return Reject("Removal already queued");
                    ring.PendingRemoval=true;
                    foreach(var c in ring.Ring.Concat(new[]{ring.Center}))PendingRemoval[c.X,c.Y]=true;
                }
                else
                {
                    if(old==Infrastructure.None||PendingRemoval[cell.X,cell.Y])return Reject("Nothing to remove");
                    PendingRemoval[cell.X,cell.Y]=true;Signals.Remove(cell);
                }
                Changed();Record(tool,cell,0,"Removal queued / previous spending retained");FinishRemovals();return true;
            }
            if(PendingRemoval[cell.X,cell.Y])return Reject("Committed trips are still using this road");
            if(!CanAffordOriginal(tool,cell))return false;
            if(tool==BuildTool.Roundabout){bool success=AddRoundabout(cell);if(success)ConsumeOriginal(tool,cell);return success;}
            if(IsMotorwayEndpoint(cell,true)&&tool==BuildTool.TrafficLight)return Reject("Traffic lights cannot replace motorway endpoints");
            if(RoundaboutAt(cell)!=null)return Reject("Use one of the roundabout's external connections");
            Infrastructure target;int cost;
            if(tool==BuildTool.TrafficLight)
            {
                if(old!=Infrastructure.Road)return Reject("Lights require an existing ordinary road");
                target=Infrastructure.TrafficLight;cost=Rules.LightCost;
                Signals[cell]=new SignalState{Cell=cell};
            }
            else if(tool==BuildTool.Bridge)
            {
                if(!Water[cell.X,cell.Y]||old!=Infrastructure.None)return Reject("A bridge tile requires empty water");
                target=Infrastructure.Bridge;cost=Rules.BridgeCost;
            }
            else if(tool==BuildTool.Road)
            {
                if(Water[cell.X,cell.Y]||old!=Infrastructure.None)return Reject("Road tile requires empty dry land");
                target=Infrastructure.Road;cost=Rules.RoadCost;
            }
            else return Reject("Unknown tool");
            ConsumeOriginal(tool,cell);
            Tiles[cell.X,cell.Y]=target;
            // Driveways are already visible before the player builds their adjoining road.
            // Attach only their designated ends; ordinary neighboring roads still need an explicit link.
            foreach(var building in Buildings)foreach(var access in Accesses(building))
                if(access+Directions[AccessDirection(building,access)]==cell)Connect(access,cell);
            Changed();Record(tool,cell,cost,$"Built {target}: +{cost}");return true;
        }
        bool Reject(string reason){LastAction=reason;return false;}
        void Changed(){NetworkVersion++;routeCache.Clear();conflictCache.Clear();foreach(var s in Signals.Values)UpdateSignalPairs(s);}
        void Record(BuildTool tool,Cell cell,int cost,string message)
        {ConstructionSpent+=cost;LastAction=message;Events.Add(new ConstructionEvent{Time=Time,Cell=cell,Tool=tool,Cost=cost,Description=message});}

        bool AddRoundabout(Cell center)
        {
            Cell[] offsets={new Cell(0,-1),new Cell(-1,0),new Cell(0,1),new Cell(1,0)};
            Cell[] ring=offsets.Select(d=>center+d).ToArray();
            foreach(var c in ring.Concat(new[]{center}))
                if(!InBounds(c)||Water[c.X,c.Y]||Blocked[c.X,c.Y]||BuildingAt(c)!=null||
                    RoundaboutAt(c)!=null||IsMotorwayEndpoint(c,true)||PendingRemoval[c.X,c.Y]||Tile(c)==Infrastructure.TrafficLight)
                    return Reject("Roundabout needs its center and four neighboring land tiles clear of buildings and upgrades");
            // Existing vehicles retain their committed lane geometry through the conversion.
            // Updated graph links route subsequent journeys around the new circle.
            var connected=new List<Cell>();
            for(int d=0;d<8;d++)if((Connections[center.X,center.Y]&(1<<d))!=0)connected.Add(center+Directions[d]);
            foreach(var n in connected)Unlink(center,n);
            foreach(var c in ring){Tiles[c.X,c.Y]=Infrastructure.Roundabout;}
            Tiles[center.X,center.Y]=Infrastructure.Roundabout;
            var state=new RoundaboutState{Center=center,Ring=ring};Roundabouts.Add(state);
            for(int i=0;i<4;i++)Link(ring[i],ring[(i+1)%4]);
            foreach(var c in ring)for(int d=0;d<8;d++)
            {
                var n=c+Directions[d];
                if(InBounds(n)&&!ring.Contains(n)&&n!=center&&Tile(n)!=Infrastructure.None&&RoundaboutAt(n)==null)
                    Link(c,n);
            }
            Changed();Record(BuildTool.Roundabout,center,Rules.RoundaboutCost,"Built roundabout: +8 / circulating lanes enabled");return true;
        }

        public bool Connect(Cell from,Cell to)
        {
            if(!InBounds(from)||!InBounds(to)||from==to||Math.Abs(from.X-to.X)>1||Math.Abs(from.Y-to.Y)>1)return Reject("Connect neighboring tile centers");
            if(!CanTraverse(from)||!CanTraverse(to))return Reject("Build both ends of this connection first");
            if(!CanConnectAcrossRail(from,to))return false;
            if(!ValidParcelLink(from,to))return Reject("Buildings connect only through their driveway");
            int d=Direction(from,to);
            if((Connections[from.X,from.Y]&(1<<d))!=0)return true;
            if(d%2==1)
            {
                var crossA=new Cell(from.X,to.Y);var crossB=new Cell(to.X,from.Y);
                if(InBounds(crossA)&&(Connections[crossA.X,crossA.Y]&(1<<Direction(crossA,crossB)))!=0)
                    return Reject("Crossing diagonal roads require a junction tile");
            }
            Link(from,to);Changed();return true;
        }
        bool ValidParcelLink(Cell a,Cell b)
        {
            foreach(var pair in new[]{(a,b),(b,a)})
            {
                var building=BuildingAt(pair.Item1);
                if(building!=null&&(!HasAccess(building,pair.Item1)||pair.Item2!=pair.Item1+Directions[AccessDirection(building,pair.Item1)]))return false;
            }
            return true;
        }
        void Link(Cell a,Cell b)
        {int d=Direction(a,b);if(d<0)return;Connections[a.X,a.Y]|=1<<d;Connections[b.X,b.Y]|=1<<((d+4)%8);}
        void Unlink(Cell a,Cell b)
        {int d=Direction(a,b);if(d<0||!InBounds(a)||!InBounds(b))return;Connections[a.X,a.Y]&=~(1<<d);Connections[b.X,b.Y]&=~(1<<((d+4)%8));}

        public bool DrawRoad(Cell from,Cell to)
        {
            if(!InBounds(from)||!InBounds(to))return Reject("Outside map");
            var cells=RasterLine(from,to);bool any=false;Cell? previous=null;
            var house=BuildingAt(from);
            if(house!=null&&house.IsHouse&&cells.Count>1&&!SetHouseDriveway(house.Id,Direction(from,cells[1])))return false;
            foreach(var c in cells)
            {
                if(!CanTraverse(c))
                {
                    if(!Build(Water[c.X,c.Y]?BuildTool.Bridge:BuildTool.Road,c)){previous=null;continue;}
                    any=true;
                }
                if(previous.HasValue&&Connect(previous.Value,c))any=true;
                previous=c;
            }
            return any;
        }
        public bool SetHouseDriveway(int id,int direction)
        {
            if(id<0||id>=Buildings.Count||!Buildings[id].IsHouse||direction<0||direction>=Directions.Length)return Reject("Choose a house and driveway direction");
            var house=Buildings[id];var outside=house.Cell+Directions[direction];
            if(!InBounds(outside)||!IsPlayable(outside)||Blocked[outside.X,outside.Y]||Water[outside.X,outside.Y]||
                BuildingAt(outside)!=null||PendingRemoval[outside.X,outside.Y]||Roundabouts.Any(r=>r.Center==outside))return Reject("Driveway needs a clear neighboring tile");
            if(direction==house.DrivewayDirection)return true;
            Unlink(house.Cell,house.Cell+Directions[house.DrivewayDirection]);house.DrivewayDirection=direction;
            // Active trips retain their lane snapshots and committed return route.
            if(CanTraverse(outside))Connect(house.Cell,outside);
            Changed();LastAction="House driveway moved";return true;
        }
        public static List<Cell> RasterLine(Cell from,Cell to)
        {
            var result=new List<Cell>();int count=Math.Max(Math.Abs(to.X-from.X),Math.Abs(to.Y-from.Y));
            for(int i=0;i<=count;i++)result.Add(count==0?from:new Cell((int)Math.Round(from.X+(to.X-from.X)*i/(double)count),(int)Math.Round(from.Y+(to.Y-from.Y)*i/(double)count)));
            return result;
        }

        public int Degree(Cell c)
        {if(!InBounds(c))return 0;int mask=Connections[c.X,c.Y],count=0;for(int d=0;d<8;d++)if((mask&(1<<d))!=0)count++;return count;}

        public void Step(int ticks=1)
        {
            if(ticks<0)throw new ArgumentOutOfRangeException(nameof(ticks));
            for(int i=0;i<ticks&&!Failed&&!ScenarioRejected;i++)
            {
                TickCount++;Time=TickCount*Rules.TickSeconds;
                UpdateOriginalInventory();UpdateCity();UpdateDestinationUpgrades();UpdateTrains();UpdateDemand();DispatchDemand();UpdateSignals();UpdateVehicles();FinishRemovals();
            }
        }

        void FinishRemovals()
        {
            FinishMotorwayRemovals();
            var committed=new HashSet<Cell>();
            foreach(var v in Cars.Where(c=>c.Stage!=TripStage.Home))
            {
                for(int i=v.RouteIndex;i<v.Lanes.Count;i++)committed.Add(v.Lanes[i].Tile);
                foreach(var c in v.ReturnRoute)committed.Add(c);
            }
            foreach(var r in Roundabouts.ToArray())
            {
                if(!r.PendingRemoval||r.Ring.Any(committed.Contains))continue;
                foreach(var c in r.Ring.Concat(new[]{r.Center}))ReleaseTile(c);Roundabouts.Remove(r);
            }
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {var c=new Cell(x,y);if(PendingRemoval[x,y]&&!committed.Contains(c)&&RoundaboutAt(c)==null)ReleaseTile(c);}
        }
        void ReleaseTile(Cell c)
        {
            for(int d=0;d<8;d++)if((Connections[c.X,c.Y]&(1<<d))!=0)Unlink(c,c+Directions[d]);
            RefundOriginal(c);
            Tiles[c.X,c.Y]=Infrastructure.None;PendingRemoval[c.X,c.Y]=false;Signals.Remove(c);Changed();
        }

        public Observation Observe()
        {
            int count=Width*Height;
            var o=new Observation{Width=Width,Height=Height,Time=Time,Day=Day,Week=Week,Hour=Hour,ConstructionSpent=ConstructionSpent,
                TripsCompleted=TripsCompleted,Failed=Failed,Scenario=Scenario.ToString(),Version=Rules.Version.ToString(),Variation=Variation.ToString(),
                ScenarioRejected=ScenarioRejected,RejectionReason=RejectionReason,RoadTilesAvailable=RoadTilesAvailable,Inventory=(int[])Inventory.Clone(),UpgradeChoices=UpgradeChoices.Select(o=>new UpgradeOffer{Type=o.Type,Amount=o.Amount,Roads=o.Roads}).ToArray(),
                UnlimitedConstruction=Rules.UnlimitedConstruction,ExactReplicaValidated=false,
                RoadCost=Rules.RoadCost,LightCost=Rules.LightCost,BridgeCost=Rules.BridgeCost,RoundaboutCost=Rules.RoundaboutCost,ConstructionGraceSeconds=Rules.ConstructionGraceSeconds,
                FidelityStatus="Unverified reconstruction; not eligible as a certified exact-original baseline",
                Objective=Rules.Version==GameVersion.Custom?"Keep city running first; less waiting and lower spending secondary. No scalar weights selected.":"Original trip score; fidelity incomplete",
                ProvisionalDefaults="Shared lane/parking/spawning approximations remain. OriginalReference is NOT an exact replica: motorway geometry/edits, inventory weighting, destination upgrades, trains, spawning and exact traffic parity remain incomplete.",
                Infrastructure=new int[count],Terrain=new int[count],BuildingColors=Enumerable.Repeat(-1,count).ToArray(),
                BuildingKinds=new int[count],Demand=new int[count],Reservations=new int[count],Connections=new int[count],PendingRemovals=new int[count],
                Vehicles=Cars.Select(v=>new VehicleState{Id=v.Id,HomeId=v.HomeId,ShopId=v.ShopId,Color=v.Color,Stage=v.Stage,ParkingSlot=v.ParkingSlot,
                    At=v.At,Next=v.Next,X=v.Position.X,Y=v.Position.Y,HeadingX=v.Heading.X,HeadingY=v.Heading.Y,Speed=v.Speed,Acceleration=v.Acceleration,
                    Waiting=v.Waiting,Progress=v.Progress,Obstacle=v.Obstacle,Route=v.Route.ToArray(),ReturnRoute=v.ReturnRoute.ToArray()}).ToArray(),
                RandomAlgorithm=random.Algorithm,RandomDraws=random.Draws,
                ScheduledSpawns=originalPlan.Select(p=>new ScheduledSpawnSnapshot{Time=p.Time,Color=p.Color,Grouping=p.Grouping,Preference=p.Preference,DemandMultiplier=p.DemandMultiplier,Attempts=p.Attempts}).ToArray(),
                Buildings=Buildings.Select(b=>new BuildingState{CarparkId=b.CarparkId,DestinationSlot=b.DestinationSlot,SharedLot=b.SharedLot,IsStation=b.IsStation,Entrances=(Cell[])b.Entrances.Clone(),Platform=(Cell[])b.Platform.Clone(),EntranceDirections=(int[])b.EntranceDirections.Clone(),Layout=b.Layout,Upgraded=b.Upgraded,DemandCapacity=DestinationCapacity(b),UpgradeAt=double.IsPositiveInfinity(b.UpgradeAt)?(double?)null:b.UpgradeAt,PlannedDemandMultiplier=b.PlannedDemandMultiplier,Id=b.Id,Color=b.Color,Cell=b.Cell,Entrance=b.Entrance,Width=b.Width,Height=b.Height,
                    IsHouse=b.IsHouse,Demand=b.Demand,Reserved=b.Reserved,DrivewayDirection=b.DrivewayDirection,OvercrowdedFor=b.OvercrowdedFor,FeasibilityVerified=b.FeasibilityVerified,
                    FeasibleDemandInterval=double.IsInfinity(b.FeasibleDemandInterval)?(double?)null:b.FeasibleDemandInterval,OriginalDemandInterval=b.OriginalDemandInterval,Parking=b.Parking==null?new int[0]:(int[])b.Parking.Clone()}).ToArray(),
                Signals=Signals.Values.Select(s=>new SignalSnapshot{Cell=s.Cell,ActivePair=s.ActivePair,Amber=s.Amber,Elapsed=s.Elapsed,Pairs=s.Pairs.ToArray()}).ToArray(),
                PlayableXMin=PlayableBounds[0],PlayableYMin=PlayableBounds[1],PlayableXMax=PlayableBounds[2],PlayableYMax=PlayableBounds[3],
                Trains=Trains.Select(t=>{var p=TrainPoint(t);return new TrainSnapshot{Id=t.Id,LineId=t.LineId,Direction=t.Direction,Stops=t.Stops,X=p.X,Y=p.Y,Speed=t.Speed,Wait=t.Wait,Distance=t.Distance};}).ToArray(),
                RailLines=RailLines.Select(l=>new RailSnapshot{Id=l.Id,Loop=l.Loop,Cells=(Cell[])l.Cells.Clone()}).ToArray(),ClosedRailCrossings=railClosedUntil.Where(p=>p.Value>=Time).Select(p=>p.Key).ToArray(),
                Motorways=Motorways.Select(m=>new MotorwaySnapshot{Id=m.Id,Number=m.Number,Start=m.Start,End=m.End,PendingRemoval=m.PendingRemoval}).ToArray(),
                Roundabouts=Roundabouts.Select(r=>new RoundaboutSnapshot{Center=r.Center,Ring=(Cell[])r.Ring.Clone(),PendingRemoval=r.PendingRemoval}).ToArray(),
                DisconnectedColorComponents=DisconnectedColorComponents(),MeanWaiting=Cars.Count==0?0:Cars.Average(c=>c.TotalWaiting)};
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {int k=y*Width+x;o.Infrastructure[k]=(int)Tiles[x,y];o.Terrain[k]=Blocked[x,y]?2:Water[x,y]?1:0;o.Connections[k]=Connections[x,y];o.PendingRemovals[k]=PendingRemoval[x,y]?1:0;}
            foreach(var b in Buildings)
                for(int y=b.Cell.Y;y<b.Cell.Y+b.Height;y++)for(int x=b.Cell.X;x<b.Cell.X+b.Width;x++)
                {int k=y*Width+x;o.BuildingColors[k]=b.Color;o.BuildingKinds[k]=b.IsHouse?1:2;o.Demand[k]=b.Demand;o.Reservations[k]=b.Reserved;}
            return o;
        }
    }
}
