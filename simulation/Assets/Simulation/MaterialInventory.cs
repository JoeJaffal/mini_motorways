using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim {
 public sealed partial class TrafficWorld {
  public int[] Inventory {get;private set;}=new int[6];
  public readonly List<UpgradeOffer> UpgradeChoices=new List<UpgradeOffer>();
  readonly Dictionary<Cell,int> bridgeSpans=new Dictionary<Cell,int>();int bridgeSerial;
  readonly HashSet<(Cell,Cell)> paidRoadConnections=new HashSet<(Cell,Cell)>();
  static (Cell,Cell) RoadEdge(Cell a,Cell b)=>a.CompareTo(b)<0?(a,b):(b,a);
  public int RoadConnectionCost(Cell a,Cell b)=>Rules.Version!=GameVersion.OriginalReference||
   BuildingAt(a)!=null||BuildingAt(b)!=null||RoundaboutAt(a)!=null||RoundaboutAt(b)!=null?0:1;
  int upgradeWeeksGranted;int[] packagesTaken=new int[6];
  readonly int[] weeksNotOffered=new int[6],totalUpgrades=new int[6];
  public void ResetInventory(){bridgeSpans.Clear();paidRoadConnections.Clear();bridgeSerial=0;Inventory=OriginalUpgrades.Starting(Map.Name);Array.Copy(Inventory,totalUpgrades,6);Array.Clear(weeksNotOffered,0,6);UpgradeChoices.Clear();upgradeWeeksGranted=0;Array.Clear(packagesTaken,0,6);}
  double UpgradeWeight(UpgradeOffer offer,UpgradeWeightProfile profile)
  {
   double bonus=0;foreach(var milestone in profile.Timeline)
    if(milestone[0]<=upgradeWeeksGranted&&totalUpgrades[offer.Type]<milestone[1])bonus=milestone[2];
   return Math.Max(0,(offer.Weight+profile.NotOfferedIncrease*weeksNotOffered[offer.Type]+bonus)*
    ReferenceCurves.Evaluate(profile.RelativeCurve,Inventory[profile.RelativeType]));
  }
  void UpdateOriginalInventory(){
   if(CustomScenarioId!=null)return; // Recorded offers replace random weekly choices in this mode only.
   if(Rules.UnlimitedConstruction||Time<Rules.SecondsPerWeek*(upgradeWeeksGranted+1)||UpgradeChoices.Count>0)return;
   upgradeWeeksGranted++;
   var profiles=OriginalGameplayTuning.UpgradeWeights(Map.Name);
   var available=OriginalUpgrades.Offers(Map.Name).Select((o,i)=>(offer:o,weight:UpgradeWeight(o,profiles[i])))
    .Where(v=>v.offer.Type<6&&v.offer.FirstWeek<=upgradeWeeksGranted&&(v.offer.LastWeek<=0||upgradeWeeksGranted<=v.offer.LastWeek)&&(v.offer.Maximum<=0||packagesTaken[v.offer.Type]<v.offer.Maximum)).ToList();
   var eligibleTypes=available.Select(v=>v.offer.Type).Distinct().ToArray();
   for(int i=0;i<2&&available.Count>0;i++){
    double total=available.Sum(v=>v.weight),value=random.NextDouble()*total;var chosen=available[available.Count-1];
    foreach(var candidate in available){value-=candidate.weight;if(value<=0){chosen=candidate;break;}}
    UpgradeChoices.Add(chosen.offer);available.Remove(chosen);
   }
   foreach(int type in eligibleTypes)weeksNotOffered[type]=UpgradeChoices.Any(o=>o.Type==type)?0:weeksNotOffered[type]+1;
   if(UpgradeChoices.Count==0)UpgradeChoices.Add(new UpgradeOffer{Type=0,Amount=20});
   Shuffle(UpgradeChoices);
  }
  public bool ChooseUpgrade(int index){
   if(Rules.UnlimitedConstruction||index<0||index>=UpgradeChoices.Count)return Reject("No such original upgrade choice");
   var offer=UpgradeChoices[index];Inventory[offer.Type]+=offer.Amount;Inventory[0]+=offer.Roads;packagesTaken[offer.Type]++;
   totalUpgrades[offer.Type]+=offer.Amount;totalUpgrades[0]+=offer.Roads;
   UpgradeChoices.Clear();LastAction="Original material package selected (selection weights still under verification)";return true;
  }
  bool CanAffordOriginal(BuildTool tool,Cell cell){
   if(Rules.UnlimitedConstruction)return true;
   if(tool==BuildTool.Road)return true; // Concrete is charged when a connection is made.
   if(tool==BuildTool.TrafficLight)return Inventory[3]>0||Reject("No traffic lights remaining");
   if(tool==BuildTool.Roundabout)return Inventory[4]>0||Reject("No roundabouts remaining");
   if(tool==BuildTool.Bridge){bool joins=Directions.Where((d,i)=>i%2==0).Any(d=>Tile(cell+d)==Infrastructure.Bridge);return joins||Inventory[1]>0||Reject("Bridge requires an available bridge");}
   return true;
  }
  void ConsumeOriginal(BuildTool tool,Cell cell){
   if(Rules.UnlimitedConstruction)return;
   if(tool==BuildTool.TrafficLight)Inventory[3]--;
   if(tool==BuildTool.Roundabout)Inventory[4]--;
   if(tool==BuildTool.Bridge){
    var ids=Directions.Where((d,i)=>i%2==0).Select(d=>cell+d).Where(bridgeSpans.ContainsKey).Select(c=>bridgeSpans[c]).Distinct().ToArray();
    int span=ids.Length==0?++bridgeSerial:ids[0];if(ids.Length==0)Inventory[1]--;
    foreach(int other in ids.Skip(1)){foreach(var key in bridgeSpans.Where(p=>p.Value==other).Select(p=>p.Key).ToArray())bridgeSpans[key]=span;Inventory[1]++;}
    bridgeSpans[cell]=span;
   }
  }
  void RefundOriginal(Cell cell){
   if(Rules.UnlimitedConstruction)return;
   switch(Tile(cell)){
    case Infrastructure.Road:break;
    case Infrastructure.TrafficLight:Inventory[3]++;break;
    case Infrastructure.Bridge:
     if(bridgeSpans.TryGetValue(cell,out int span)){bridgeSpans.Remove(cell);if(!bridgeSpans.Values.Contains(span))Inventory[1]++;}break;
    case Infrastructure.Roundabout:if(Roundabouts.Any(r=>r.Center==cell))Inventory[4]++;break;
   }
  }
 }
}
