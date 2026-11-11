// Diagnostic only: per-tick fingerprint of a scenario run (trips, every car's lane and position).
using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
class Timeline{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
using var o=new StreamWriter(a[1]);
while(!s.Complete){s.AdvanceTick();var w=s.World;
 o.WriteLine($"{w.Time:0.00} {w.TripsCompleted} "+string.Join(";",w.Cars.Where(c=>c.Moving).Select(c=>$"{c.Id}:{c.CurrentLane.Key}:{c.DistanceAlongLane:0.0000}:{c.Obstacle}")));}}}
