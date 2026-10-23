using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim {
 public sealed partial class TrafficWorld {
  public int[] Inventory {get;private set;}=new int[6];
  public readonly List<UpgradeOffer> UpgradeChoices=new List<UpgradeOffer>();
  readonly Dictionary<Cell,int> bridgeSpans=new Dictionary<Cell,int>();int bridgeSerial;
  int upgradeWeeksGranted;int[] packagesTaken=new int[6];
  public void ResetInventory(){bridgeSpans.Clear();bridgeSerial=0;Inventory=OriginalUpgrades.Starting(Map.Name);UpgradeChoices.Clear();upgradeWeeksGranted=0;Array.Clear(packagesTaken,0,6);}
  void UpdateOriginalInventory(){
   if(Rules.UnlimitedConstruction||Time<Rules.SecondsPerWeek*(upgradeWeeksGranted+1)||UpgradeChoices.Count>0)return;
   upgradeWeeksGranted++;
   var available=OriginalUpgrades.Offers(Map.Name).Where(o=>o.Type<6&&o.FirstWeek<=upgradeWeeksGranted&&(o.LastWeek<=0||upgradeWeeksGranted<=o.LastWeek)&&(o.Maximum<=0||packagesTaken[o.Type]<o.Maximum)).ToList();
   for(int i=0;i<2&&available.Count>0;i++){
    double total=available.Sum(o=>o.Weight),value=random.NextDouble()*total;var chosen=available[available.Count-1];
    foreach(var offer in available){value-=offer.Weight;if(value<=0){chosen=offer;break;}}
    UpgradeChoices.Add(chosen);available.Remove(chosen);
   }
  }
  public bool ChooseUpgrade(int index){
   if(Rules.UnlimitedConstruction||index<0||index>=UpgradeChoices.Count)return Reject("No such original upgrade choice");
   var offer=UpgradeChoices[index];Inventory[offer.Type]+=offer.Amount;Inventory[0]+=offer.Roads;packagesTaken[offer.Type]++;
   UpgradeChoices.Clear();LastAction="Original material package selected (selection weights still under verification)";return true;
  }
  bool CanAffordOriginal(BuildTool tool,Cell cell){
   if(Rules.UnlimitedConstruction)return true;
   if(tool==BuildTool.Road)return Inventory[0]>0||Reject("No road tiles remaining");
   if(tool==BuildTool.TrafficLight)return Inventory[3]>0||Reject("No traffic lights remaining");
   if(tool==BuildTool.Roundabout)return Inventory[4]>0||Reject("No roundabouts remaining");
   if(tool==BuildTool.Bridge){bool joins=Directions.Where((d,i)=>i%2==0).Any(d=>Tile(cell+d)==Infrastructure.Bridge);return Inventory[0]>0&&(joins||Inventory[1]>0)||Reject("Bridge requires road tiles and an available bridge");}
   return true;
  }
  void ConsumeOriginal(BuildTool tool,Cell cell){
   if(Rules.UnlimitedConstruction)return;
   if(tool==BuildTool.Road)Inventory[0]--;
   if(tool==BuildTool.TrafficLight)Inventory[3]--;
   if(tool==BuildTool.Roundabout)Inventory[4]--;
   if(tool==BuildTool.Bridge){
    Inventory[0]--;var ids=Directions.Where((d,i)=>i%2==0).Select(d=>cell+d).Where(bridgeSpans.ContainsKey).Select(c=>bridgeSpans[c]).Distinct().ToArray();
    int span=ids.Length==0?++bridgeSerial:ids[0];if(ids.Length==0)Inventory[1]--;
    foreach(int other in ids.Skip(1)){foreach(var key in bridgeSpans.Where(p=>p.Value==other).Select(p=>p.Key).ToArray())bridgeSpans[key]=span;Inventory[1]++;}
    bridgeSpans[cell]=span;
   }
  }
  void RefundOriginal(Cell cell){
   if(Rules.UnlimitedConstruction)return;
   switch(Tile(cell)){
    case Infrastructure.Road:Inventory[0]++;break;
    case Infrastructure.TrafficLight:Inventory[0]++;Inventory[3]++;break;
    case Infrastructure.Bridge:
     Inventory[0]++;if(bridgeSpans.TryGetValue(cell,out int span)){bridgeSpans.Remove(cell);if(!bridgeSpans.Values.Contains(span))Inventory[1]++;}break;
    case Infrastructure.Roundabout:if(Roundabouts.Any(r=>r.Center==cell))Inventory[4]++;break;
   }
  }
 }
}
