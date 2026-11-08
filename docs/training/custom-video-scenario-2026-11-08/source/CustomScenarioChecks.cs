using System;
using System.Linq;
namespace MotorwaysSim
{
    public static class CustomScenarioChecks
    {
        static void Check(bool condition,string message){if(!condition)throw new InvalidOperationException("CUSTOM SCENARIO CHECK FAILED: "+message);}
        static CustomScenarioDefinition Fixture()=>new CustomScenarioDefinition{schemaVersion=1,id="scenario-regression",city="LosAngeles",seed=17,referenceScore=835,duration=80,
            events=new[]{
                new CustomScenarioEvent{kind="house",id="h1",at=0,x=28,y=5,color=0,direction=0},
                new CustomScenarioEvent{kind="shop",id="s1",at=0,x=35,y=3,color=0,layout=0},
                new CustomScenarioEvent{kind="draw",at=1,x=28,y=5,toX=35,toY=5},
                new CustomScenarioEvent{kind="offer",at=2,offers=new[]{new CustomScenarioOffer{type=0,amount=1,roads=0}}},
                new CustomScenarioEvent{kind="choose",at=2,choice=0}}};
        public static int Run()
        {
            var definition=Fixture();var a=new CustomScenarioSession(definition);var b=new CustomScenarioSession(Fixture());
            Check(a.World.Buildings.Count==2&&a.CompletedEvents==2,"time-zero recorded spawns replace random city");
            Check(a.World.Inventory[0]==25&&a.World.TripsCompleted==0,"reference score is never injected");
            while(!a.Complete){a.AdvanceTick();b.AdvanceTick();}
            Check(a.World.TripsCompleted>0&&a.World.TripsCompleted==b.World.TripsCompleted&&a.World.Time==b.World.Time,"productive deterministic playback");
            Check(a.Audit.SequenceEqual(b.Audit)&&a.CompletedEvents==5,"stable input order and action audit");
            Check(a.World.Buildings.Count==2&&a.World.UpgradeChoices.Count==0,"no random growth or reward leaks");
            a.World.Reset(42,ScenarioKind.LosAngeles);
            Check(a.World.CustomScenarioId==null&&a.World.Rules.EnableCityGrowth,"ordinary reset restores standard growth");
            bool rejected=false;var invalid=Fixture();invalid.events[0].x=0;invalid.events[0].y=0;
            try{new CustomScenarioSession(invalid);}catch(InvalidOperationException){rejected=true;}
            Check(rejected,"invalid observed placement is rejected, not silently relocated");
            invalid=Fixture();invalid.events[0].at=double.NaN;rejected=false;
            try{new CustomScenarioSession(invalid);}catch(ArgumentException){rejected=true;}
            Check(rejected,"nonfinite timing rejected");
            var roads=new TrafficWorld(17,false,Rules.ForVersion(GameVersion.OriginalReference));
            roads.LoadCustomScenario(new CustomScenarioDefinition{id="connection-check",city="LosAngeles",seed=17});
            var start=new Cell(28,5);var end=new Cell(29,5);int stock=roads.Inventory[0];
            Check(roads.DrawRoad(start,end)&&roads.Inventory[0]==stock-1,"one connection costs one road");
            Check(roads.RemoveRoadConnection(start,end)&&roads.Inventory[0]==stock,"unused erased connection refunds once");
            Check(!roads.RemoveRoadConnection(start,end)&&roads.Inventory[0]==stock,"duplicate erase cannot duplicate refund");
            Check(roads.DrawRoad(start,end)&&roads.Inventory[0]==stock-1,"redrawing refunded edge charges normally");
            return 4;
        }
    }
}
