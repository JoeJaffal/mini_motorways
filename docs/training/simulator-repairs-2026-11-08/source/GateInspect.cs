using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{public string Throats()=>string.Join("; ",carparkThroats.Select(t=>$"lot {t.Key.Item1} access {t.Key.Item2} owner {t.Value}"));
 public string CarText(int id){var c=CarById(id);return $"car {id} {c.Stage} shop {c.ShopId} lane {(c.Moving?c.CurrentLane.Key:"-")} d={c.DistanceAlongLane:0.000} v={c.Speed:0.0000} wait {c.Waiting:0.0} obstacle '{c.Obstacle}' shove {c.Shoving} next {string.Join(" ",c.Lanes.Skip(c.RouteIndex+1).Take(3).Select(l=>l.Key))}";}}}
class GateInspect{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
var ids=a[2].Split(',').Select(int.Parse).ToArray();
foreach(var t in a[1].Split(',').Select(double.Parse)){while(s.World.Time<t-1e-9&&!s.Complete)s.AdvanceTick();var w=s.World;
 Console.WriteLine($"== t={w.Time:0.00} throats: {w.Throats()}");foreach(int id in ids)Console.WriteLine("  "+w.CarText(id));
 var lot=w.Buildings.Where(b=>!b.IsHouse&&b.CarparkId==20).Select(b=>$"{b.Id}@{b.Cell} c{b.Color} demand {b.Demand} parking [{string.Join(",",b.Parking)}] entrances {string.Join(" ",b.Entrances)}");Console.WriteLine("  lot20: "+string.Join(" | ",lot));}}}
