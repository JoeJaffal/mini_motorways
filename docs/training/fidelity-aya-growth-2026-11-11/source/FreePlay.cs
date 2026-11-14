using System;using System.Linq;using System.Collections.Generic;using MotorwaysSim;
static class P{
 static double Near(TrafficWorld w,Building h){double best=double.PositiveInfinity;foreach(var d in w.Buildings.Where(b=>!b.IsHouse&&b.Color==h.Color)){var c=w.DestinationCenter(d);double dx=h.Cell.X+.5-c.X,dy=h.Cell.Y+.5-c.Y;best=Math.Min(best,Math.Sqrt(dx*dx+dy*dy));}return best;}
 static void Dump(ScenarioKind map,int seed,double t){
   var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=1e9;
   var w=new TrafficWorld(seed,false,rules);w.Reset(seed,map);while(w.Time<t)w.Step(100);
   var pb=w.PlayableBounds;
   for(int y=0;y<30;y++){var row=new char[50];for(int x=0;x<50;x++){var c=new Cell(x,y);char ch=w.Water[x,y]?'~':w.Blocked[x,y]?'#':w.Rails[x,y]?'=':(x>=pb[0]&&x<pb[2]&&y>=pb[1]&&y<pb[3])?'.':' ';
     var b=w.BuildingAt(c);if(b!=null){ch=b.IsHouse?(char)('0'+b.Color):(char)('A'+w.Buildings.Where(o=>!o.IsHouse&&o.CarparkId==b.CarparkId).Min(o=>o.Color));if(b.IsHouse){var o2=b.Cell+TrafficWorld.Directions[b.DrivewayDirection];}}
     row[x]=ch;}Console.WriteLine(new string(row));}
   foreach(var s in w.Observe().ScheduledSpawns.Where(s=>s.Attempts>0))Console.WriteLine($"pending color {s.Color} grouping {s.Grouping} pref {s.Preference} attempts {s.Attempts} time {s.Time:F0}");
 }
 static void Main(string[] a){
  if(a.Length>0&&a[0]=="--dump"){Dump(Enum.Parse<ScenarioKind>(a[1]),int.Parse(a[2]),double.Parse(a[3]));return;}
  var maps=new[]{ScenarioKind.LosAngeles,ScenarioKind.London};
  if(a.Length>0)maps=a.Select(s=>Enum.Parse<ScenarioKind>(s)).ToArray();
  Console.WriteLine("version "+SimulatorVersion.Value);
  foreach(var map in maps)for(int seed=1;seed<=5;seed++){
   var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=1e9;
   var w=new TrafficWorld(seed,false,rules);w.Reset(seed,map);var sw=System.Diagnostics.Stopwatch.StartNew();
   foreach(double t in new[]{600.0,1200.0}){
    while(w.Time<t&&!w.Failed&&!w.ScenarioRejected)w.Step(100);
    var houses=w.Buildings.Where(b=>b.IsHouse).ToList();var dest=w.Buildings.Where(b=>!b.IsHouse).ToList();
    var dists=houses.Select(h=>Near(w,h)).Where(d=>!double.IsInfinity(d)).ToList();
    int adj=houses.Count(h=>dest.Any(d=>h.Cell.X>=d.Cell.X-1&&h.Cell.X<=d.Cell.X+d.Width&&h.Cell.Y>=d.Cell.Y-1&&h.Cell.Y<=d.Cell.Y+d.Height));
    Console.WriteLine($"{map} seed {seed} t={w.Time:F0} houses {houses.Count} destinations {dest.Count} lots {dest.Select(d=>d.CarparkId).Distinct().Count()} upgraded {dest.Count(d=>d.Upgraded)} meanHouseToOwnDest {(dists.Count>0?dists.Average():0):F2} housesTouchingLots {adj} wall {sw.Elapsed.TotalSeconds:F1}s");
   }}
 }}
