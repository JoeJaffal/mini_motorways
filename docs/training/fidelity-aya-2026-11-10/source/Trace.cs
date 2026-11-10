using System;using System.Linq;using System.Text.Json;using System.IO;using System.Collections.Generic;using System.Reflection;using MotorwaysSim;
public static class Trace{
 public static void Main(string[] a){
  // usage: Harness <scenario.json> <out.csv|-> [phase0 phase1 phase2 phase3 phase4]  (phases in days)
  var def=JsonSerializer.Deserialize<CustomScenarioDefinition>(File.ReadAllText(a[0]),new JsonSerializerOptions{PropertyNameCaseInsensitive=true,IncludeFields=true,PropertyNamingPolicy=JsonNamingPolicy.CamelCase,Converters={new System.Text.Json.Serialization.JsonStringEnumConverter()}});
  var s=new CustomScenarioSession(def);var w=s.World;double next=0;
  if(a.Length>=7){var ph=(Dictionary<int,double>)typeof(TrafficWorld).GetField("demandGroupPhases",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(w);
   for(int c=0;c<5;c++)ph[c]=double.Parse(a[2+c],System.Globalization.CultureInfo.InvariantCulture);}
  var o=a[1]=="-"?null:new StreamWriter(a[1]);
  o?.WriteLine("t,score,demand,reserved,cars,moving,waiting5,houses,dests,maxOver");
  while(!s.Complete){s.AdvanceTick();if(o!=null&&w.Time>=next){next+=10;
   var d=w.Buildings.Where(b=>!b.IsHouse).ToList();
   o.WriteLine($"{w.Time:F1},{w.TripsCompleted},{d.Sum(b=>b.Demand)},{d.Sum(b=>b.Reserved)},{w.Cars.Count(c=>c.Stage!=TripStage.Home)},{w.Cars.Count(c=>c.Stage!=TripStage.Home&&c.Speed>0.02)},{w.Cars.Count(c=>c.Waiting>5)},{w.Buildings.Count(b=>b.IsHouse)},{d.Count},{(d.Count>0?d.Max(b=>b.OvercrowdedFor):0):F1}");o.Flush();}}
  var line=$"# end t={w.Time:F2} score={w.TripsCompleted} failed={w.Failed} events={s.CompletedEvents}/{def.events.Length}";
  o?.WriteLine(line);o?.Close();Console.WriteLine(line);
  {var phd=(Dictionary<int,double>)typeof(TrafficWorld).GetField("demandGroupPhases",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(w);Console.WriteLine("phases "+string.Join(" ",phd.OrderBy(k=>k.Key).Select(k=>k.Key+":"+k.Value.ToString("F3"))));}
  if(Environment.GetEnvironmentVariable("DUMP_DESTS")=="1")foreach(var b in w.Buildings.Where(b=>!b.IsHouse))Console.WriteLine($"D {b.Id} {b.Color} {b.SpawnTime:F2} {b.Upgraded}@{b.UpgradeAt:F2} {b.PlannedDemandMultiplier} {b.IsStation} {b.Cell.X},{b.Cell.Y} served={b.Served} demand={b.Demand} created={b.Served+b.Demand}");
 }}
