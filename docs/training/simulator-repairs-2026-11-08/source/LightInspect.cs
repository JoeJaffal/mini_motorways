using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{public string Approaches(Cell junction){var sig=Signals[junction];return string.Join(" | ",Cars.Where(c=>c.Moving).Select(c=>TryApproach(c,junction,out var lane,out double d)?$"car {c.Id} in {lane.Incoming} approach {(lane.Incoming+4)%8} green={(sig.ActivePair&(1<<((lane.Incoming+4)%8)))!=0} d={d:0.00} '{c.Obstacle}' v={c.Speed:0.000}":null).Where(x=>x!=null));}}}
class LightInspect{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));var cell=new Cell(20,13);
foreach(var t in new[]{1050.0,1080,1120,1146}){while(s.World.Time<t-1e-9&&!s.Complete)s.AdvanceTick();var w=s.World;var sig=w.Signals[cell];
 Console.WriteLine($"t={w.Time:0} pairs [{string.Join(",",sig.Pairs)}] active {sig.ActivePair} amber {sig.Amber} overtime {sig.Overtime} elapsed {sig.Elapsed:0.0} minNearby {w.Rules.SignalMinimumNearbyCars} nearbyDist {w.Rules.SignalNearbyDistance}");
 Console.WriteLine("   "+w.Approaches(cell));}}}
