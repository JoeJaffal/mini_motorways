// Diagnostic only: per-tick state of one car between two times. Usage: CarTrace scenario.json carId from to
using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
class CarTrace{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
int id=int.Parse(a[1]);double from=double.Parse(a[2]),to=double.Parse(a[3]);double lastT=-1;int ticks=0;
while(!s.Complete&&s.World.Time<=to){s.AdvanceTick();ticks++;var w=s.World;if(w.Time<from||w.Time==lastT&&false)continue;
 var c=w.Cars[id];Console.WriteLine($"tick {ticks} t={w.Time:0.00} stage={c.Stage} moving={c.Moving} speed={c.Speed:0.0000} wait={c.Waiting:0.00} total={c.TotalWaiting:0.00} obstacle='{c.Obstacle}' lane={(c.Moving?c.CurrentLane.Key:"")} d={c.DistanceAlongLane:0.0000}");lastT=w.Time;}}}
