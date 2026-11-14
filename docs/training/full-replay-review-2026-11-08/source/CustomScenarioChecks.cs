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
            var oldEnd=new Cell(35,8);var neighbor=new Cell(36,8);var newEnd=new Cell(35,10);
            roads.Inventory[2]=1;
            Check(roads.DrawRoad(oldEnd,neighbor)&&roads.AddMotorway(start,oldEnd),"motorway with surface connection");
            Check(roads.RemoveRoadConnection(oldEnd,neighbor)&&roads.Tile(oldEnd)==Infrastructure.Road,"erased endpoint retained while motorway exists");
            Check(roads.EditMotorway(roads.Motorways.Single(m=>!m.PendingRemoval).Id,start,newEnd),"move cleared motorway endpoint");
            roads.Step();
            Check(roads.Tile(oldEnd)==Infrastructure.None,"erased old endpoint cleans up after motorway retirement");
            Check(roads.Tile(start)==Infrastructure.Road,"unrelated paid road remains intact");
            var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;rules.OvercrowdingSeconds=100000;
            var signals=new TrafficWorld(42,false,rules);signals.Reset(42,ScenarioKind.EmptyLab);signals.Inventory[0]=1000;signals.Inventory[3]=1;
            var home=signals.SpawnBuilding(new Cell(5,12),0,true);var shop=signals.SpawnBuilding(new Cell(20,10),0,false);
            Check(signals.DrawRoad(home.Access,shop.Access)&&signals.DrawRoad(new Cell(15,12),new Cell(15,8)),"signal retirement network built");
            Check(signals.Build(BuildTool.TrafficLight,new Cell(15,12)),"signal installed");
            shop.Demand=2;shop.DemandCountdown=1e9;bool erased=false;
            for(int tick=0;tick<6000;tick++)
            {
                signals.Step();
                if(!erased&&signals.Cars.Any(c=>c.Moving&&c.Position.X>13&&c.Position.X<15))
                {Check(signals.RemoveRoadConnection(new Cell(14,12),new Cell(15,12)),"erase committed signal approach");erased=true;}
                if(erased&&signals.TripsCompleted==2&&signals.ActiveCars==0)break;
            }
            Check(erased&&signals.TripsCompleted==2&&signals.ActiveCars==0,"retired approach retains phase through delivery and return");
            var direct=new TrafficWorld(42,false,rules);direct.Reset(42,ScenarioKind.EmptyLab);direct.Inventory[2]=1;
            var directHome=direct.SpawnBuilding(new Cell(5,12),0,true);var directShop=direct.SpawnBuilding(new Cell(20,10),0,false);
            int concrete=direct.Inventory[0];
            Check(direct.AddMotorway(new Cell(6,12),new Cell(19,12)),"motorway on existing native driveway ends");
            Check(direct.Inventory[0]==concrete&&direct.Tile(new Cell(19,12))==Infrastructure.None,"native motorway attachment adds no paid road");
            Check(direct.FindRoute(directHome.Access,directShop.Access).Count==4,"both native stubs attach without a surface draw");
            directShop.Demand=2;directShop.DemandCountdown=1e9;
            for(int tick=0;tick<6000;tick++){direct.Step();if(direct.TripsCompleted==2&&direct.ActiveCars==0)break;}
            Check(direct.TripsCompleted==2&&direct.ActiveCars==0,"direct native motorway delivers and returns");
            foreach(bool turn in new[]{false,true})
            {
                var native=new TrafficWorld(42,false,rules);native.Reset(42,ScenarioKind.EmptyLab);
                var nativeHome=native.SpawnBuilding(turn?new Cell(5,13):new Cell(5,12),0,true,turn?6:0);
                var nativeShop=native.SpawnBuilding(new Cell(7,10),0,false);int nativeStock=native.Inventory[0];
                if(turn){Check(native.FindRoute(nativeHome.Access,nativeShop.Access).Count==0,"separate native ends do not connect");Check(native.SetHouseDriveway(nativeHome.Id,7),"turn to shared native endpoint");}
                Check(native.FindRoute(nativeHome.Access,nativeShop.Access).Count==3,"native ends meet through their common endpoint");
                Check(native.Tile(new Cell(6,12))==Infrastructure.None&&native.Inventory[0]==nativeStock,"native join needs no paid road");
                nativeShop.Demand=2;nativeShop.DemandCountdown=1e9;
                for(int tick=0;tick<6000;tick++){native.Step();if(native.TripsCompleted==2&&native.ActiveCars==0)break;}
                Check(native.TripsCompleted==2&&native.ActiveCars==0,"native join delivers and returns");
            }
            return 9;
        }
    }
}
