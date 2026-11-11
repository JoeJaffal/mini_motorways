using System;
using System.Diagnostics;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using MotorwaysSim;

sealed class Request
{
    public string Command { get; set; } = "observe";
    public int Seed { get; set; } = 42;
    public bool Connected { get; set; }
    public int Ticks { get; set; } = 1;
    public string Tool { get; set; } = "Road";
    public int X { get; set; }
    public int Y { get; set; }
    public int Choice {get;set;}
    public int Id {get;set;}
    public int ToX { get; set; }
    public int ToY { get; set; }
    public string Scenario { get; set; }
    public string Version { get; set; }
    public bool RequireExact {get;set;}
    public bool IncludeConnectivity {get;set;}
    public string Variation { get; set; } = "SameMap";
}

static class Program
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions {
        IncludeFields=true,PropertyNamingPolicy=JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive=true,
        Converters={new JsonStringEnumConverter()}
    };

    public static void Main(string[] args)
    {
        int scenarioArg=Array.IndexOf(args,"--run-scenario");
        if(scenarioArg>=0)
        {
            CustomScenarioSession session=null;
            try
            {
                if(scenarioArg+1>=args.Length)throw new ArgumentException("Missing scenario file");
                var definition=JsonSerializer.Deserialize<CustomScenarioDefinition>(System.IO.File.ReadAllText(args[scenarioArg+1]),Json);
                session=new CustomScenarioSession(definition);var timer=Stopwatch.StartNew();
                while(!session.Complete){if(timer.Elapsed.TotalSeconds>120)throw new TimeoutException("Custom scenario exceeded120-second wall limit");session.AdvanceTick();}
                Console.WriteLine(JsonSerializer.Serialize(new{result="COMPLETED",mode="custom-scenario-reconstruction",definition.id,definition.seed,
                    referenceScore=definition.referenceScore,score=session.World.TripsCompleted,difference=session.World.TripsCompleted-definition.referenceScore,
                    seconds=session.World.Time,failed=session.World.Failed,events=session.CompletedEvents,totalEvents=definition.events.Length,inventory=session.World.Inventory,
                    destinations=session.World.Buildings.Where(b=>!b.IsHouse).Select(b=>new{b.Id,b.Color,b.Cell,b.Entrance,b.Demand,b.Reserved,b.Served,b.OvercrowdedFor}),
                    cars=session.World.Cars.Select(c=>new{c.Id,c.HomeId,c.ShopId,c.Stage,c.At,c.Next,c.Waiting,c.Obstacle,c.ParkingSlot,c.RouteIndex,c.DistanceAlongLane,c.Speed,position=new[]{c.Position.X,c.Position.Y},heading=new[]{c.Heading.X,c.Heading.Y},lanes=c.Lanes.Skip(c.RouteIndex).Select(l=>new{l.Key,l.Length,samples=l.Samples.Select(p=>new[]{p.X,p.Y})}),c.Route,c.ReturnRoute}),audit=session.Audit},Json));
            }
            catch(Exception error)
            {
                if(session!=null)Console.WriteLine(JsonSerializer.Serialize(new{result="REJECTED_EVENT",error=error.Message,
                    score=session.World.TripsCompleted,seconds=session.World.Time,failed=session.World.Failed,
                    events=session.CompletedEvents,totalEvents=session.Definition.events.Length,audit=session.Audit},Json));
                Console.Error.WriteLine(error.Message);Environment.ExitCode=1;
            }
            return;
        }
        int replayArg=Array.IndexOf(args,"--verify-replay");
        if(replayArg>=0)
        {
            try
            {
                if(replayArg+1>=args.Length)throw new ArgumentException("Missing replay file");
                var recording=JsonSerializer.Deserialize<AiReplayRecording>(System.IO.File.ReadAllText(args[replayArg+1]),Json);
                var replay=new AiReplaySession(recording);
                while(!replay.Complete)replay.AdvanceTick();
                Console.WriteLine(JsonSerializer.Serialize(new {result="PASS",recording.seed,score=replay.World.TripsCompleted,
                    seconds=replay.World.Time,commands=replay.CompletedCommands},Json));
            }
            catch(Exception error){Console.Error.WriteLine(error.Message);Environment.ExitCode=1;}
            return;
        }
        if(Array.IndexOf(args,"--self-test")>=0){Console.WriteLine(SimulationChecks.Run());return;}
        if(Array.IndexOf(args,"--evaluate-crossings")>=0)
        {
            for(int seed=40;seed<44;seed++)
            {
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=100000;
                var city=new TrafficWorld(seed,false,rules);
                for(int tick=0;tick<8000;tick++){if(tick%200==0){city.Inventory[0]=1000;city.BuildReferenceNetwork();}city.Step();}
                Console.WriteLine(JsonSerializer.Serialize(new {seed,city.Time,city.TripsCompleted,
                    waitsOver20Seconds=city.Cars.Count(c=>c.Waiting>20),city.ActiveCars,
                    fixture="400 seconds; debug roads every 10 seconds; road stock replenished; failure timer extended"},Json));
            }
            return;
        }
        if(Array.IndexOf(args,"--evaluate-city")>=0)
        {
            for(int seed=0;seed<5;seed++)
            {
                var city=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.Custom));var timer=Stopwatch.StartNew();
                while(!city.Failed&&!city.ScenarioRejected&&city.Time<300){city.BuildReferenceNetwork();city.Step(400);}
                Console.WriteLine(JsonSerializer.Serialize(new {seed,city.Time,city.TripsCompleted,city.DemandTotal,city.ConstructionSpent,
                    city.Failed,city.ScenarioRejected,city.RejectionReason,version=city.Rules.Version.ToString(),buildings=city.Buildings.Count,cars=city.Cars.Count,wallSeconds=timer.Elapsed.TotalSeconds,
                    terminated=city.Failed,truncated=!city.Failed},Json));
            }
            return;
        }
        if(Array.IndexOf(args,"--benchmark")>=0)
        {
            var timer=Stopwatch.StartNew();int ticks=0,trips=0;
            for(int seed=0;seed<10;seed++)
            {
                var w=new TrafficWorld(seed,true,Rules.ForVersion(GameVersion.Custom));
                while(!w.Failed&&!w.ScenarioRejected&&w.Time<300){w.Step();ticks++;}
                trips+=w.TripsCompleted;
            }
            Console.WriteLine(JsonSerializer.Serialize(new {ticks,trips,wallSeconds=timer.Elapsed.TotalSeconds,
                ticksPerSecond=ticks/timer.Elapsed.TotalSeconds},Json));return;
        }
        var world=new TrafficWorld(42,false);
        bool includeConnectivity=false;
        string line;
        while((line=Console.ReadLine())!=null)
        {
            try
            {
                var request=JsonSerializer.Deserialize<Request>(line,Json)??throw new Exception("Missing request");
                if(request.Command=="quit")break;
                int trips=world.TripsCompleted,spending=world.ConstructionSpent;bool accepted=true;
                if(request.Command=="drawchoices")
                {
                    Console.WriteLine(JsonSerializer.Serialize(new {accepted=true,terminated=world.Failed,truncated=world.ScenarioRejected,
                        possibleChanges=world.DrawChangeChoices(new Cell(request.X,request.Y))},Json));continue;
                }
                switch(request.Command)
                {
                    case "reset":
                        var version=request.Version==null?world.Rules.Version:Enum.Parse<GameVersion>(request.Version,true);
                        var scenario=request.Scenario==null?(request.Connected?ScenarioKind.ReferenceLab:ScenarioKind.LosAngeles):Enum.Parse<ScenarioKind>(request.Scenario,true);
                        if(!Enum.IsDefined(typeof(GameVersion),version)||!Enum.IsDefined(typeof(ScenarioKind),scenario))throw new Exception("Unknown version or scenario");
                        if(request.RequireExact)throw new Exception("Exact-original parity is not yet validated. OriginalReference remains under development.");
                        world=new TrafficWorld(request.Seed,false,Rules.ForVersion(version));
                        world.Reset(request.Seed,scenario,Enum.Parse<MapVariation>(request.Variation,true));
                        includeConnectivity=request.IncludeConnectivity;
                        trips=0;spending=0;break;
                    case "upgrade":accepted=world.ChooseUpgrade(request.Choice);break;
                    case "motorway":accepted=world.AddMotorway(new Cell(request.X,request.Y),new Cell(request.ToX,request.ToY));break;
                    case "editMotorway":accepted=world.EditMotorway(request.Id,new Cell(request.X,request.Y),new Cell(request.ToX,request.ToY));break;
                    case "removeMotorway":accepted=world.RemoveMotorway(request.Id);break;
                    case "connect":accepted=world.Connect(new Cell(request.X,request.Y),new Cell(request.ToX,request.ToY));break;
                    case "driveway":accepted=world.SetHouseDriveway(request.Id,TrafficWorld.Direction(new Cell(request.X,request.Y),new Cell(request.ToX,request.ToY)));break;
                    case "draw":accepted=world.DrawRoad(new Cell(request.X,request.Y),new Cell(request.ToX,request.ToY));break;
                    case "reference":accepted=world.BuildReferenceNetwork();break;
                    case "step":
                        if(request.Ticks<0||request.Ticks>100000)throw new Exception("ticks must be 0..100000");
                        world.Step(request.Ticks);break;
                    case "build":
                        if(!Enum.TryParse<BuildTool>(request.Tool,true,out var tool)||!Enum.IsDefined(typeof(BuildTool),tool))
                            throw new Exception("Unknown construction tool");
                        accepted=world.Build(tool,new Cell(request.X,request.Y));break;
                    case "observe":break;
                    default:throw new Exception("Commands: reset, build, connect, draw, motorway, editMotorway, removeMotorway, upgrade, reference (debug), step, observe, quit");
                }
                Console.WriteLine(JsonSerializer.Serialize(new {accepted,message=world.LastAction,
                    networkVersion=world.NetworkVersion,
                    tripsDelta=world.TripsCompleted-trips,spendingDelta=world.ConstructionSpent-spending,
                    terminated=world.Failed,truncated=world.ScenarioRejected,
                    usefulConnectedHouses=includeConnectivity&&(request.Command=="reset"||request.Command=="step"||request.Command=="observe")
                        ?(int?)world.UsefulConnectedHouseCount():null,
                    usefulConnectivity=includeConnectivity&&(request.Command=="reset"||request.Command=="step"||request.Command=="observe")
                        ?world.UsefulConnectivityState():null,
                    observation=world.Observe()},Json));
            }
            catch(Exception exception)
            {Console.WriteLine(JsonSerializer.Serialize(new {error=exception.Message},Json));}
        }
    }
}
