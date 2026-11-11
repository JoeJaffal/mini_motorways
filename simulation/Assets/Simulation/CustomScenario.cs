using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    [Serializable] public sealed class CustomScenarioDefinition
    {
        public int schemaVersion=1,seed,referenceScore;
        public string id,city="LosAngeles",source,sourceSha256,uncertainties;
        public double duration;
        public int[] startingInventory;
        public int[] paletteRgb;
        public double[] bounds;
        public CustomScenarioEvent[] events;
    }
    [Serializable] public sealed class CustomScenarioOffer { public int type,amount,roads; }
    [Serializable] public sealed class CustomScenarioEvent
    {
        public double at,videoTime=-1;
        // Optional, destination events only: the time the original's plan scheduled this destination, when the
        // recording shows it arriving later. Between the two the original retries placement every 20 s and adds
        // extra demand to the colour (GenerateDemandProcess.BalanceDemandFromFailedSpawns).
        public double scheduledAt=-1;
        public string kind,id,target,tool;
        public int x,y,toX,toY,color,direction,layout,choice;
        public CustomScenarioOffer[] offers;
        public bool allowRejection;
    }
    public sealed partial class TrafficWorld
    {
        public string CustomScenarioId {get;private set;}
        internal void SetReplayDelayedDestinations(List<(int color,int attempts)> delayed)
        {
            originalPlan.RemoveAll(p=>p.Order==-1);
            foreach(var d in delayed)originalPlan.Add(new ScheduledSpawn{Time=double.PositiveInfinity,Type=0,Color=d.color,DemandMultiplier=1,Attempts=d.attempts,Order=-1});
        }
        double[] customScenarioBounds;
        bool? growthBeforeCustomScenario;
        public void LoadCustomScenario(CustomScenarioDefinition definition)
        {
            if(definition==null||definition.schemaVersion!=1||string.IsNullOrWhiteSpace(definition.id)||
                !Enum.TryParse<ScenarioKind>(definition.city,out var city)||!CityCatalog.Maps.Contains(city)||
                Rules.Version!=GameVersion.OriginalReference)throw new ArgumentException("Invalid Original custom scenario");
            var bounds=definition.bounds??new double[]{0,0,Width,Height};
            if(bounds.Length!=4||bounds.Any(v=>double.IsNaN(v)||double.IsInfinity(v))||
                bounds[0]<0||bounds[1]<0||bounds[2]>Width||bounds[3]>Height||bounds[0]>=bounds[2]||bounds[1]>=bounds[3])
                throw new ArgumentException("Invalid custom scenario bounds");
            if(definition.startingInventory!=null&&(definition.startingInventory.Length!=6||definition.startingInventory.Any(v=>v<0)))
                throw new ArgumentException("Custom starting inventory needs six nonnegative values");
            if(definition.paletteRgb!=null&&(definition.paletteRgb.Length<1||definition.paletteRgb.Length>6||definition.paletteRgb.Any(v=>v<0||v>0xffffff)))
                throw new ArgumentException("Custom palette must contain RGB colors");
            Reset(definition.seed,ScenarioKind.EmptyLab);
            Scenario=city;Map=CityCatalog.Get(city);CustomScenarioId=definition.id;customScenarioBounds=(double[])bounds.Clone();
            boundsTime=double.NaN;
            growthBeforeCustomScenario=Rules.EnableCityGrowth;Rules.EnableCityGrowth=false;random=new SimulationRandom(definition.seed,GameVersion.OriginalReference);
            ResetInventory();if(definition.startingInventory!=null)Array.Copy(definition.startingInventory,Inventory,6);
            Array.Copy(Inventory,totalUpgrades,6);
            for(int y=0;y<Height;y++)for(int x=0;x<Width;x++)
            {
                char t=Map.Terrain[y][x];Water[x,y]=t=='~';Blocked[x,y]=t=='#'||t=='^';
                Unzoneable[x,y]=t==':'||t=='#'||t=='~'||t=='^'||t=='=';
                Rails[x,y]=Map.RailLines.Any(line=>line.Cells.Contains(new Cell(x,y)));
            }
            InitializeRailways();Changed();LastAction="Custom scenario: "+definition.id;
        }
    }
    public sealed class CustomScenarioSession
    {
        public readonly TrafficWorld World;
        public readonly CustomScenarioDefinition Definition;
        readonly CustomScenarioEvent[] events;
        readonly Dictionary<string,int> buildings=new Dictionary<string,int>(),motorways=new Dictionary<string,int>();
        public readonly List<string> Audit=new List<string>();
        public int CompletedEvents {get;private set;}
        public bool Complete=>World.Failed||World.Time+1e-8>=Definition.duration;
        public CustomScenarioSession(CustomScenarioDefinition definition)
        {
            if(definition==null||definition.events==null||definition.events.Length>100000||
                double.IsNaN(definition.duration)||double.IsInfinity(definition.duration)||definition.duration<=0||definition.duration>86400)
                throw new ArgumentException("Invalid custom timeline");
            foreach(var e in definition.events)
                if(e==null||double.IsNaN(e.at)||double.IsInfinity(e.at)||e.at<0||e.at>definition.duration)
                    throw new ArgumentException("Invalid custom event time");
            Definition=definition;events=definition.events.Select((e,i)=>(e,i)).OrderBy(v=>v.e.at).ThenBy(v=>v.i).Select(v=>v.e).ToArray();
            World=new TrafficWorld(definition.seed,false,Rules.ForVersion(GameVersion.OriginalReference));World.LoadCustomScenario(definition);
            ApplyDue();
        }
        public void AdvanceTick()
        {
            if(Complete)return;
            World.Step();ApplyDue();UpdateDelayedDestinations();
        }
        // Destinations the recording shows arriving after their scheduled time count as delayed plan entries until they
        // appear, with one failed attempt per 20 s retry, so the simulator's own failed-spawn demand rule applies.
        void UpdateDelayedDestinations()
        {
            var delayed=new List<(int color,int attempts)>();
            for(int i=CompletedEvents;i<events.Length;i++)
            {
                var e=events[i];
                if(e.scheduledAt<0||e.scheduledAt>World.Time||(e.kind!="shop"&&e.kind!="shared"&&e.kind!="join"))continue;
                delayed.Add((e.color,1+(int)Math.Floor((World.Time-e.scheduledAt)/20)));
            }
            World.SetReplayDelayedDestinations(delayed);
        }
        void ApplyDue()
        {
            while(!World.Failed&&CompletedEvents<events.Length&&events[CompletedEvents].at<=World.Time+1e-8)
            {
                var e=events[CompletedEvents];bool accepted=Apply(e);
                Audit.Add(World.Time.ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+" "+e.kind+" "+(accepted?"accepted":"REJECTED: "+World.LastAction));
                if(!accepted&&!e.allowRejection)throw new InvalidOperationException("Custom event "+CompletedEvents+" ("+e.kind+" at "+e.at+") rejected: "+World.LastAction);
                CompletedEvents++;
            }
        }
        bool Apply(CustomScenarioEvent e)
        {
            var from=new Cell(e.x,e.y);var to=new Cell(e.toX,e.toY);
            switch(e.kind)
            {
                case "house":case "shop":case "shared":case "join":
                    if(string.IsNullOrEmpty(e.id)||buildings.ContainsKey(e.id))throw new ArgumentException("Building IDs must be unique and nonempty");
                    Building b=e.kind=="shared"?World.SpawnSharedCarpark(from,e.color,e.layout):
                        e.kind=="join"?World.JoinSharedCarpark(buildings[e.target],e.color):World.SpawnBuilding(from,e.color,e.kind=="house",e.direction,e.layout);
                    if(b==null)return false;buildings.Add(e.id,b.Id);return true;
                case "circle":World.Buildings[buildings[e.target]].Upgraded=true;return true;
                case "draw":
                    if(!World.DrawRoad(from,to))return false;
                    var cells=TrafficWorld.RasterLine(from,to);
                    for(int i=1;i<cells.Count;i++)
                        if((World.Connections[cells[i-1].X,cells[i-1].Y]&(1<<TrafficWorld.Direction(cells[i-1],cells[i])))==0)return false;
                    return true;
                case "driveway":return World.SetHouseDriveway(buildings[e.target],e.direction);
                case "erase":return World.RemoveRoadConnection(from,to);
                case "build":
                    if(!Enum.TryParse<BuildTool>(e.tool,out var tool)||!Enum.IsDefined(typeof(BuildTool),tool)||tool==BuildTool.Motorway)throw new ArgumentException("Invalid scenario build tool");
                    return World.Build(tool,from);
                case "motorway":
                    if(string.IsNullOrEmpty(e.id)||motorways.ContainsKey(e.id))throw new ArgumentException("Motorway IDs must be unique");
                    if(!World.AddMotorway(from,to))return false;motorways.Add(e.id,World.Motorways.Last().Id);return true;
                case "editMotorway":
                    if(!World.EditMotorway(motorways[e.target],from,to))return false;motorways[e.target]=World.Motorways.Last().Id;return true;
                case "removeMotorway":return World.RemoveMotorway(motorways[e.target]);
                case "offer":
                    if(e.offers==null||e.offers.Length<1||e.offers.Any(o=>o==null||o.type<0||o.type>5||o.amount<0||o.roads<0))throw new ArgumentException("Invalid recorded upgrade offers");
                    if(World.UpgradeChoices.Count>0)throw new ArgumentException("An earlier upgrade choice is still pending");
                    World.UpgradeChoices.AddRange(e.offers.Select(o=>new UpgradeOffer{Type=o.type,Amount=o.amount,Roads=o.roads}));return true;
                case "choose":return World.ChooseUpgrade(e.choice);
                default:throw new ArgumentException("Unknown scenario event: "+e.kind);
            }
        }
    }
}
