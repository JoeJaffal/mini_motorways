// Diagnostic only: lane-conflict facts at the 19,7/19,8 jam and destination overcrowding timeline.
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{
 public Lane LaneOf(int car,string key)=>Cars[car].Lanes.FirstOrDefault(l=>l.Key==key);
 public bool ConflictPublic(Lane a,Lane b)=>Conflicts(a,b);
 public string RoundaboutsText()=>string.Join(";",Roundabouts.Select(r=>$"center {r.Center} ring {string.Join(",",r.Ring)}"));}}
class JamInspect{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));double next=1100;
while(!s.Complete){s.AdvanceTick();var w=s.World;
 if(w.Time+1e-9>=next){next+=10;var over=w.Buildings.Where(b=>!b.IsHouse&&b.OvercrowdedFor>0).Select(b=>$"{b.Id}@{b.Cell} c{b.Color} demand {b.Demand} over {b.OvercrowdedFor:0.0}");Console.WriteLine($"t={w.Time:0.00} trips={w.TripsCompleted} overcrowded: {string.Join(" | ",over)}");}
 if(Math.Abs(w.Time-1163)<1e-6){
  Console.WriteLine("roundabouts: "+w.RoundaboutsText());
  var lanes=new Dictionary<string,Lane>();
  foreach(var (car,key) in new[]{(52,"19:7:2:2"),(6,"19:7:2:0"),(22,"19:7:6:6"),(22,"19:8:5:6"),(15,"19:8:2:3")}){var l=w.LaneOf(car,key);Console.WriteLine($"lane {key} via car {car}: {(l==null?"missing":$"tile {l.Tile} junction {l.IsJunction} ring {l.IsRoundabout} length {l.Length:0.000}")}");if(l!=null)lanes[key]=l;}
  foreach(var p in new[]{("19:7:6:6","19:7:2:2"),("19:7:6:6","19:7:2:0"),("19:7:2:0","19:7:2:2"),("19:8:2:3","19:8:5:6")})
   if(lanes.ContainsKey(p.Item1)&&lanes.ContainsKey(p.Item2))Console.WriteLine($"Conflicts({p.Item1},{p.Item2}) = {w.ConflictPublic(lanes[p.Item1],lanes[p.Item2])}");
  foreach(int id in new[]{6,15,22,27,28,52}){var c=w.Cars[id];Console.WriteLine($"car {id} {c.Stage} lane {c.CurrentLane.Key} d={c.DistanceAlongLane:0.000}/{c.CurrentLane.Length:0.000} next {string.Join(" ",c.Lanes.Skip(c.RouteIndex+1).Take(3).Select(l=>l.Key))}");}}}
var W=s.World;Console.WriteLine($"end t={W.Time:0.00} failed={W.Failed} trips={W.TripsCompleted}; "+string.Join(" | ",W.Buildings.Where(b=>!b.IsHouse&&b.OvercrowdedFor>0).Select(b=>$"{b.Id}@{b.Cell} c{b.Color} over {b.OvercrowdedFor:0.00}")));}}
