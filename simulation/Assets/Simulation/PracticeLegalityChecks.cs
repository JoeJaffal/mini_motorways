using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public static class PracticeLegalityChecks
    {
        static void Check(bool condition,string message){if(!condition)throw new InvalidOperationException("Practice mask check: "+message);}
        public static int Run()
        {
            int checkedActions=0;var random=new Random(90531);
            for(int scenario=0;scenario<20;scenario++)
            {
                int seed=500+scenario,stock=scenario%3==0?0:20;
                var history=new List<Action<TrafficWorld>>();
                TrafficWorld Fresh(){var w=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.OriginalReference));w.LoadConnectionPractice(seed);w.Inventory[0]=stock;foreach(var action in history)action(w);return w;}
                var world=Fresh();
                for(int actionIndex=0;actionIndex<50;actionIndex++)
                {
                    Cell from;
                    if(actionIndex%3==0)
                    {
                        var b=world.Buildings[actionIndex%world.Buildings.Count];
                        from=new Cell(b.Cell.X+random.Next(-1,b.Width+1),b.Cell.Y+random.Next(-1,b.Height+1));
                    }
                    else from=new Cell(random.Next(TrafficWorld.Width),random.Next(TrafficWorld.Height));
                    int direction=random.Next(8);var to=from+TrafficWorld.Directions[direction];
                    bool erase=actionIndex%5==0,remove=actionIndex%7==0;
                    var before=world.Observe();string message=world.LastAction;
                    var sources=world.PracticeSources();
                    var choices=world.PracticeDirections(erase?"erase":"draw",from);
                    var after=world.Observe();
                    Check(before.RandomDraws==after.RandomDraws&&before.Time==after.Time&&message==world.LastAction,"query changed clock/random/action");
                    Check(before.Connections.SequenceEqual(after.Connections)&&before.Infrastructure.SequenceEqual(after.Infrastructure)&&before.Inventory.SequenceEqual(after.Inventory),"query mutated network/stock");
                    Check(before.Buildings.Select(b=>b.DrivewayDirection).SequenceEqual(after.Buildings.Select(b=>b.DrivewayDirection)),"query turned a driveway");
                    int index=from.Y*TrafficWorld.Width+from.X;
                    if(world.InBounds(from))Check((erase?sources.erase[index]:sources.draw[index])==choices.Any(v=>v),"prefix hides or admits a completion incorrectly");
                    var twin=Fresh();
                    bool predicted=remove?world.InBounds(from)&&sources.remove[index]:choices[direction];
                    bool accepted=remove?twin.Build(BuildTool.Remove,from):erase?twin.RemoveRoadConnection(from,to):twin.DrawRoad(from,to);
                    Check(predicted==accepted,$"acceptance mismatch seed{seed} action{actionIndex} from{from} to{to} erase{erase} remove{remove}: predicted{predicted}, native{accepted}");
                    Action<TrafficWorld> commit=remove?w=>w.Build(BuildTool.Remove,from):erase?w=>w.RemoveRoadConnection(from,to):w=>w.DrawRoad(from,to);
                    commit(world);history.Add(commit);
                    checkedActions++;
                }
            }
            return checkedActions+TrafficCases();
        }

        static int TrafficCases()
        {
            int count=0;var random=new Random(6051);
            for(int scenario=0;scenario<5;scenario++)
            {
                int seed=800+scenario;var history=new List<Action<TrafficWorld>>();
                var path=new List<Cell>();
                TrafficWorld Fresh()
                {
                    var w=new TrafficWorld(seed,false,Rules.ForVersion(GameVersion.OriginalReference));w.LoadConnectionPractice(seed);
                    var house=w.Buildings.First(b=>b.IsHouse);var shop=w.Buildings.First(b=>!b.IsHouse);
                    var target=shop.Access+TrafficWorld.Directions[shop.DrivewayDirection];var at=house.Cell;
                    if(path.Count==0)path.Add(at);
                    while(at!=target)
                    {
                        var next=new Cell(at.X+Math.Sign(target.X-at.X),at.Y+Math.Sign(target.Y-at.Y));
                        Check(w.DrawRoad(at,next),"test witness rejected");at=next;
                        if(history.Count==0&&!path.Contains(at))path.Add(at);
                    }
                    w.Step(400);w.Inventory[0]=scenario%2==0?0:20;
                    foreach(var action in history)action(w);
                    return w;
                }
                var world=Fresh();
                for(int index=0;index<20;index++)
                {
                    var from=path[random.Next(path.Count)];int d=random.Next(8);var to=from+TrafficWorld.Directions[d];
                    bool erase=index%2==0;
                    var before=world.Observe();var choices=world.PracticeDirections(erase?"erase":"draw",from);
                    var after=world.Observe();
                    Check(before.RandomDraws==after.RandomDraws&&before.Inventory.SequenceEqual(after.Inventory)&&before.Connections.SequenceEqual(after.Connections),"live-traffic query mutation");
                    var twin=Fresh();bool accepted=erase?twin.RemoveRoadConnection(from,to):twin.DrawRoad(from,to);
                    Check(choices[d]==accepted,$"live-traffic acceptance seed{seed} index{index} {from}->{to}");
                    Action<TrafficWorld> change=erase?w=>w.RemoveRoadConnection(from,to):w=>w.DrawRoad(from,to);
                    change(world);history.Add(change);
                    if(index%5==0){world.Step(20);history.Add(w=>w.Step(20));}
                    count++;
                }
            }
            for(int d=0;d<8;d++)
            {
                var w=new TrafficWorld(15,false,Rules.ForVersion(GameVersion.OriginalReference));w.LoadConnectionPractice(15);
                var from=new Cell(2,2);var to=from+TrafficWorld.Directions[d];
                Check(w.PracticeDirections("draw",from)[d]&&w.DrawRoad(from,to),"legal diagonal/cardinal omitted");
                Check(w.PracticeDirections("draw",from)[d]&&w.DrawRoad(from,to),"harmless repeated connection omitted");
                count+=2;
            }
            return count;
        }
    }
}
