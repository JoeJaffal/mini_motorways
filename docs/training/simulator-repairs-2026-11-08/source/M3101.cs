// Diagnostic only: replay one AI recording and report shop 9, the lights placed near it, and blocked chains.
using System;using System.Collections.Generic;using System.Linq;using System.Text.Json;using System.IO;using MotorwaysSim;
namespace MotorwaysSim{public sealed partial class TrafficWorld{
 public string LightText(Cell c){if(!Signals.TryGetValue(c,out var s))return $"{c}: none";var cand=SignalCandidates(c);
  return $"{c}: active {s.ActivePair} amber {s.Amber} overtime {s.Overtime} elapsed {s.Elapsed:0.0} pairs [{string.Join(",",s.Pairs)}] nearby {NearbyCount(s,cand)} cands {string.Join(" ",cand.Select(x=>$"c{x.Car.Id}/a{x.Approach}/d{x.Distance:0.00}/{x.Car.Speed:0.00}/'{x.Car.Obstacle}'"))}";}
 public List<(int car,int blocker,string why)> Blocks(){var snap=Cars.Where(c=>c.Moving).Select(c=>new MotionSnapshot{Car=c,Lane=c.CurrentLane,Index=c.RouteIndex,Distance=c.DistanceAlongLane,Speed=c.Speed,Acceleration=c.Acceleration,Position=c.Position}).ToList();
  var r=new List<(int,int,string)>();foreach(var st in snap){var car=st.Car;if(car.Speed>=.02)continue;double gap=1e6;int leader=-1;
   foreach(var o in snap){if(o.Car.Id==car.Id)continue;double d=double.PositiveInfinity;if(o.Lane.Key==st.Lane.Key){double x=o.Distance-st.Distance;if(x>1e-8||Math.Abs(x)<1e-8&&o.Car.Id<car.Id)d=Math.Max(0,x);}else{double ahead=st.Lane.Length-st.Distance;for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++){if(car.Lanes[i].Key==o.Lane.Key){d=ahead+o.Distance;break;}ahead+=car.Lanes[i].Length;if(ahead>Rules.LookaheadDistance)break;}}if(d<gap){gap=d;leader=o.Car.Id;}}
   if(leader>=0&&gap-Rules.CarLength-Rules.FollowingGap<.02)r.Add((car.Id,leader,"queue"));
   double ad=st.Lane.Length-st.Distance;for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++){var l=car.Lanes[i];if(ad<Rules.LookaheadDistance&&!MayEnter(car,l,snap,out string why,out int b)){r.Add((car.Id,b,why+" "+l.Key));break;}ad+=l.Length;if(ad>Rules.LookaheadDistance)break;}}
  return r;}}}
class M3101{static void Main(string[] a){
var opt=new JsonSerializerOptions{IncludeFields=true,PropertyNameCaseInsensitive=true,Converters={new System.Text.Json.Serialization.JsonStringEnumConverter()}};
var s=new AiReplaySession(JsonSerializer.Deserialize<AiReplayRecording>(File.ReadAllText(a[0]),opt));var w=s.World;var times=a[1].Split(',').Select(double.Parse).ToArray();int k=0;
while(!s.Complete&&k<times.Length){s.AdvanceTick();if(w.Time+1e-9<times[k])continue;k++;
 var shop=w.Buildings.First(b=>b.Id==9);Console.WriteLine($"== t={w.Time:0.0} trips {w.TripsCompleted} shop9 @{shop.Cell} entrance {shop.Entrance} color {shop.Color} demand {shop.Demand} reserved {shop.Reserved} served {shop.Served} over {shop.OvercrowdedFor:0.0} parking [{string.Join(",",shop.Parking)}]");
 foreach(var c in new[]{new Cell(10,12)})Console.WriteLine("   light "+w.LightText(c));
 var to9=w.Cars.Where(c=>c.ShopId==9).ToList();Console.WriteLine($"   cars for shop9: {to9.Count}: "+string.Join(" | ",to9.Select(c=>$"{c.Id} {c.Stage} at {c.At} '{c.Obstacle}' w{c.Waiting:0}")));
 Console.WriteLine("   connections (10,12): "+w.Connections[10,12]+" gate owners: "+string.Join(",",w.Cars.Where(c=>c.ShopId==9&&c.Moving).Select(c=>c.Id+":"+c.Lanes.Skip(c.RouteIndex).Select(l=>l.Key).FirstOrDefault())));}}}
