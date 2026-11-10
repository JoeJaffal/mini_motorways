using System;using System.Linq;using MotorwaysSim;
public static class Overlap{
 public static void Run(){
  foreach(bool shared in new[]{false,true}){
   var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
   var w=new TrafficWorld(40,false,rules);w.Reset(40,ScenarioKind.EmptyLab);w.Inventory[0]=1000;w.Rules.OvercrowdingSeconds=100000;
   var shop=shared?w.SpawnSharedCarpark(new Cell(20,10),0):w.SpawnBuilding(new Cell(20,10),0,false);
   foreach(var cell in new[]{new Cell(5,12),new Cell(5,15),new Cell(5,18),new Cell(5,21)}){var home=w.SpawnBuilding(cell,0,true);w.DrawRoad(home.Access,new Cell(10,cell.Y));w.DrawRoad(new Cell(10,cell.Y),new Cell(10,12));}
   w.DrawRoad(new Cell(10,12),shop.Access);shop.Demand=8;shop.DemandCountdown=1e9;
   var seen=new System.Collections.Generic.HashSet<string>();int n=0;
   for(int tick=0;tick<6000;tick++){w.Step();var m=w.Cars.Where(c=>c.Moving&&c.CurrentLane.IsParking).ToArray();
    for(int i=0;i<m.Length;i++)for(int j=i+1;j<m.Length;j++)if(Point.Distance(m[i].Position,m[j].Position)<.2){n++;
      var k=m[i].CurrentLane.Key+" | "+m[j].CurrentLane.Key;if(seen.Add(k))Console.WriteLine($"shared={shared} t={w.Time:F2} {k} d={Point.Distance(m[i].Position,m[j].Position):F3} sp={m[i].Speed:F2},{m[j].Speed:F2}");}}
   Console.WriteLine($"shared={shared} overlapping car-pair ticks={n} trips={w.TripsCompleted}");}
 }}
