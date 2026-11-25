using System;
using System.Linq;

namespace MotorwaysSim
{
    [Serializable]
    public sealed class AiReplayAction
    {
        public string command,tool;
        public int x,y,toX,toY,id,choice,ticks;
        public bool accepted;
        public int afterTrips;
        public double afterTime;
    }

    [Serializable]
    public sealed class AiReplayRecording
    {
        public int schemaVersion,seed,score,policySteps,episode;
        public string version,scenario,variation,simulatorCommit,source,policySchema,ranking;
        public double duration;
        public bool terminated,truncated;
        public AiReplayAction[] actions;
    }

    // Serializer-independent so the same recording runs in .NET and Unity.
    // Commands use normal rules; replay never grants materials or uses helpers.
    public sealed class AiReplaySession
    {
        public readonly AiReplayRecording Recording;
        public readonly TrafficWorld World;
        public int CompletedCommands {get;private set;}
        public bool Complete=>CompletedCommands==Recording.actions.Length;
        int remainingTicks;

        public AiReplaySession(AiReplayRecording recording)
        {
            if(recording==null||recording.schemaVersion!=1||recording.version!="OriginalReference"||
               recording.actions==null||recording.actions.Length==0||recording.actions.Length>1000000)
                throw new ArgumentException("Unsupported or empty AI replay");
            if(!Enum.TryParse<ScenarioKind>(recording.scenario,out var scenario)||!CityCatalog.Maps.Contains(scenario)||
               recording.variation!="SameMap")throw new ArgumentException("Unsupported replay map or variation");
            if(recording.score<0||double.IsNaN(recording.duration)||double.IsInfinity(recording.duration)||recording.duration<0)
                throw new ArgumentException("Invalid replay outcome");
            foreach(var action in recording.actions)
                if(action==null||action.ticks!=20||double.IsNaN(action.afterTime)||double.IsInfinity(action.afterTime)||
                   action.afterTime<0||action.afterTrips<0)throw new ArgumentException("Invalid replay transition");
            Recording=recording;
            World=new TrafficWorld(recording.seed,false,Rules.ForVersion(GameVersion.OriginalReference));
            World.Reset(recording.seed,scenario,MapVariation.SameMap);
        }

        public void AdvanceTick()
        {
            if(Complete)return;
            var a=Recording.actions[CompletedCommands];
            if(remainingTicks==0)
            {
                bool accepted=Apply(a);
                if(accepted!=a.accepted)throw new InvalidOperationException("AI replay acceptance diverged at command "+(CompletedCommands+1));
                remainingTicks=a.ticks;
            }
            World.Step();remainingTicks--;
            if(remainingTicks!=0)return;
            if(World.TripsCompleted!=a.afterTrips||Math.Abs(World.Time-a.afterTime)>0.00001)
                throw new InvalidOperationException("AI replay score/time diverged at command "+(CompletedCommands+1));
            CompletedCommands++;
            if(Complete&&(World.TripsCompleted!=Recording.score||Math.Abs(World.Time-Recording.duration)>0.00001||
                World.Failed!=Recording.terminated||World.ScenarioRejected))
                throw new InvalidOperationException("AI replay final outcome diverged");
        }

        bool Apply(AiReplayAction a)
        {
            var start=new Cell(a.x,a.y);var end=new Cell(a.toX,a.toY);
            switch(a.command)
            {
                case "wait":return true;
                case "draw":return World.DrawRoad(start,end);
                case "build":
                    if(!Enum.TryParse<BuildTool>(a.tool,out var tool)||!Enum.IsDefined(typeof(BuildTool),tool)||tool==BuildTool.Motorway)
                        throw new ArgumentException("Unsupported replay tool");
                    return World.Build(tool,start);
                case "driveway":return World.SetHouseDriveway(a.id,TrafficWorld.Direction(start,end));
                case "motorway":return World.AddMotorway(start,end);
                case "editMotorway":return World.EditMotorway(a.id,start,end);
                case "removeMotorway":return World.RemoveMotorway(a.id);
                case "upgrade":return World.ChooseUpgrade(a.choice);
                default:throw new ArgumentException("Replay command is not a normal gameplay action: "+a.command);
            }
        }
    }
}
