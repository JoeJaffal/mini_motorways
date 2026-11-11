using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
class ShoveCount{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
int shoveTicks=0;var cars=new System.Collections.Generic.HashSet<int>();var first=new System.Collections.Generic.List<string>();double over=0;
while(!s.Complete){s.AdvanceTick();var w=s.World;foreach(var c in w.Cars.Where(c=>c.Shoving)){shoveTicks++;if(cars.Add(c.Id)&&first.Count<8)first.Add($"t={w.Time:0.00} car {c.Id} lane {c.ShovingLane}");}}
var W=s.World;Console.WriteLine($"end t={W.Time:0.00} trips={W.TripsCompleted} shove-car-ticks={shoveTicks} cars-that-shoved={cars.Count}");foreach(var f in first)Console.WriteLine("  "+f);
Console.WriteLine("overcrowded: "+string.Join(" | ",W.Buildings.Where(b=>!b.IsHouse&&b.OvercrowdedFor>0).Select(b=>$"{b.Id}@{b.Cell} c{b.Color} {b.OvercrowdedFor:0.0}s served {b.Served}")));}}
