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
  // Original GameBehaviourModel: a link costs 1 unless an end is a house, destination or carpark; ring tiles count as
  // empty tiles, so a link from outside into a ring tile costs 1 (links inside a roundabout are its own lanes).
  public int RoadConnectionCost(Cell a,Cell b)=>Rules.Version!=GameVersion.OriginalReference||
   BuildingAt(a)!=null||BuildingAt(b)!=null||RoundaboutAt(a)!=null&&RoundaboutAt(b)!=null?0:1;
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
   // Original GameBehaviourModel.GenerateNextUpgradeChoices: the weights and their total are computed once; a pick
   // removes the package from the list but not its weight, so later picks read the remaining packages against the
   // original weight positions and total, falling back to the last package when the draw is not used up.
   var packages=available.Select(v=>v.offer).ToList();var weights=available.Select(v=>v.weight).ToList();double total=weights.Sum();
   for(int i=0;i<2&&packages.Count>0;i++){
    double value=random.NextDouble()*total;int pick=packages.Count-1;
    for(int j=0;j<packages.Count;j++){value-=weights[j];if(value<=0){pick=j;break;}}
    UpgradeChoices.Add(packages[pick]);packages.RemoveAt(pick);
   }
   // OnUpgradeNotPresented for every package left (per package, so a type can count twice), then OnUpgradePresented.
   foreach(var left in packages)weeksNotOffered[left.Type]++;
   foreach(var shown in UpgradeChoices)weeksNotOffered[shown.Type]=0;
   if(UpgradeChoices.Count==0)return; // the original grants an empty concrete package: nothing to choose
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
   if(tool==BuildTool.Bridge){bool joins=Rules.Version==GameVersion.OriginalReference&&bridgeFrom.HasValue?bridgeSpans.ContainsKey(bridgeFrom.Value):
    Directions.Where((d,i)=>i%2==0).Any(d=>Tile(cell+d)==Infrastructure.Bridge);return joins||Inventory[1]>0||Reject("Bridge requires an available bridge");}
   return true;
  }
  void ConsumeOriginal(BuildTool tool,Cell cell){
   if(Rules.UnlimitedConstruction)return;
   if(tool==BuildTool.TrafficLight)Inventory[3]--;
   if(tool==BuildTool.Roundabout)Inventory[4]--;
   if(tool==BuildTool.Bridge){
    // Original Passage: a crossing starts (one bridge) when a link goes from land onto a water tile without roads and
    // extends for free from water already on it; spans follow links, so parallel bridges are separate crossings.
    // (A tile built directly with the bridge tool has no stroke predecessor and keeps the adjacency grouping.)
    var ids=Rules.Version==GameVersion.OriginalReference&&bridgeFrom.HasValue?(bridgeSpans.TryGetValue(bridgeFrom.Value,out int from)?new[]{from}:new int[0]):
     Directions.Where((d,i)=>i%2==0).Select(d=>cell+d).Where(bridgeSpans.ContainsKey).Select(c=>bridgeSpans[c]).Distinct().ToArray();
    int span=ids.Length==0?++bridgeSerial:ids[0];if(ids.Length==0)Inventory[1]--;
    foreach(int other in ids.Skip(1)){foreach(var key in bridgeSpans.Where(p=>p.Value==other).Select(p=>p.Key).ToArray())bridgeSpans[key]=span;Inventory[1]++;}
    bridgeSpans[cell]=span;
   }
  }
  Cell? bridgeFrom; // stroke cell preceding a bridge being built (OriginalReference crossing rule)
  // Original AddRoadEdit: a link joining two separate crossings makes one, returning a bridge.
  void MergeBridgeSpans(Cell a,Cell b){
   if(Rules.Version!=GameVersion.OriginalReference||Rules.UnlimitedConstruction)return;
   if(!bridgeSpans.TryGetValue(a,out int keep)||!bridgeSpans.TryGetValue(b,out int other)||keep==other)return;
   foreach(var key in bridgeSpans.Where(p=>p.Value==other).Select(p=>p.Key).ToArray())bridgeSpans[key]=keep;Inventory[1]++;
  }
  // Original TileEditor.WouldConnectionPassPassageConstraints (bridges): a water tile holds at most two roads, so a
  // link may not give one a third (roads erased but still in use count); a link may not start from a water tile with
  // no road; restoring an erased link is always allowed. (A diagonal that would cross another at a corner is refused
  // in Connect when it starts or ends on water.)
  int OriginalRoadCount(Cell c)=>Degree(c)+retiredConnectionConcrete.Keys.Count(e=>e.Item1==c||e.Item2==c);
  string WaterLinkViolation(Cell from,Cell to){
   if(Rules.Version!=GameVersion.OriginalReference)return null;
   bool a=Water[from.X,from.Y],b=Water[to.X,to.Y];if(!a&&!b)return null;
   if(retiredConnectionConcrete.ContainsKey(RoadEdge(from,to)))return null;
   if(a&&OriginalRoadCount(from)>1||b&&OriginalRoadCount(to)>1)return "Cannot build a bridge that would create an intersection";
   if(a&&OriginalRoadCount(from)==0)return "Cannot build a new bridge from an empty water tile";
   return null;
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
