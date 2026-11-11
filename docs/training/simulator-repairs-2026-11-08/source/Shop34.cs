using System;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{public string Throats()=>string.Join("; ",carparkThroats.Select(t=>$"lot {t.Key.Item1} {t.Key.Item2}->{t.Value}"));public int Phys(Vehicle c)=>PhysicalCarpark(c);}}
class Shop34{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true};
var s=new CustomScenarioSession(JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),opt));
foreach(var t in new[]{975.0,985,1070}){while(s.World.Time<t-1e-9&&!s.Complete)s.AdvanceTick();var w=s.World;
 Console.WriteLine($"t={w.Time:0} throats {w.Throats()}");
 foreach(var c in w.Cars.Where(c=>c.Moving&&w.Phys(c)==20||c.Stage==TripStage.Parking&&(c.ShopId==20||c.ShopId==34)))
  Console.WriteLine($"   car {c.Id} {c.Stage} shop {c.ShopId} lane {(c.Moving?c.CurrentLane.Key:"bay "+c.ParkingSlot)} d={c.DistanceAlongLane:0.000} v={c.Speed:0.000} wait {c.Waiting:0.0} '{c.Obstacle}' shove={c.Shoving} next {string.Join(" ",c.Lanes.Skip(c.RouteIndex+1).Take(2).Select(l=>l.Key))}");}}}
