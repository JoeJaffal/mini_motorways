using System;
using System.Linq;
using System.Collections.Generic;
namespace MotorwaysSim
{
    // Focused checks for OriginalReference free-play placement (decisions 085-088).
    public static class OriginalPlacementChecks
    {
        static void Require(bool value,string message){if(!value)throw new InvalidOperationException("PLACEMENT CHECK FAILED: "+message);}
        static TrafficWorld City(ScenarioKind map,int seed)
        {
            var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.OvercrowdingSeconds=1e9;
            var w=new TrafficWorld(seed,false,rules);w.Reset(seed,map);return w;
        }
        static bool Near(Building b,Cell c,int ring)=>c.X>=b.Cell.X-ring&&c.X<b.Cell.X+b.Width+ring&&c.Y>=b.Cell.Y-ring&&c.Y<b.Cell.Y+b.Height+ring;
        public static int Run()
        {
            int suites=0;
            {
                // Influence factors as the original's ScaleTileWeightByBuildingInfluence.
                const int far=int.MaxValue;var H=TrafficWorld.PlacementKind.House;var D=TrafficWorld.PlacementKind.Destination;
                Require(TrafficWorld.ScaleByBuildingInfluence(1,H,1,1,far,far,far,0)==0,"no house within one step of a destination");
                Require(TrafficWorld.ScaleByBuildingInfluence(1,H,1,far,far,0,far,0)==0&&TrafficWorld.ScaleByBuildingInfluence(1,D,0,far,far,far,0,0)==0,"no building on a house tile");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,H,2,far,far,3,far,0)-Math.Pow(.6,4))<1e-12,"far house push 0.6^(7-d)");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,H,1,far,far,3,far,4)-Math.Pow(1.3-4*.035,4))<1e-12,"near house pull weakens per neighbour");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,H,1,far,far,3,far,9)-Math.Pow(1.05,4))<1e-12,"near house pull floor 1.05");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,H,0,far,2,far,far,0)-Math.Pow(.425,5))<1e-12,"own destination pushes houses 0.425^(7-d)");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,H,0,far,far,far,3,0)-Math.Pow(.9,2))<1e-12,"other-colour house push 0.9^((7-d)/2)");
                Require(Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,D,2,far,5,far,far,0)-Math.Pow(.6,7))<1e-12&&
                    Math.Abs(TrafficWorld.ScaleByBuildingInfluence(1,D,1,far,5,far,far,0)-Math.Pow(1.3,7))<1e-12&&
                    TrafficWorld.ScaleByBuildingInfluence(1,D,0,far,5,2,far,0)==1,"destination far/near over radius 12; houses never weigh destinations");
                suites++;
            }
            {
                // Playable area includes both edges; placement keeps one tile clear of it on every side.
                var w=City(ScenarioKind.LosAngeles,3);var t=w.PlayableTiles;var b=w.PlayableBounds;
                Require(b[2]==Math.Min(TrafficWorld.Width,t[2]+1)&&b[3]==Math.Min(TrafficWorld.Height,t[3]+1),"exclusive stored maximum is the inclusive tile + 1");
                Require(w.IsPlayable(new Cell(t[2],t[3]))&&w.IsPlayable(new Cell(t[0],t[1]))&&!w.IsPlayable(new Cell(t[2]+1,t[3])),"both playable edges included");
                w.PlaceableArea(out int x0,out int y0,out int x1,out int y1);
                Require(x0==t[0]+1&&y0==t[1]+1&&x1==t[2]-1&&y1==t[3]-1,"placement inset one tile");
                foreach(var building in w.Buildings)
                    Require(building.Cell.X>=x0&&building.Cell.Y>=y0&&building.Cell.X+building.Width-1<=x1&&building.Cell.Y+building.Height-1<=y1,"initial buildings inside the inset area");
                suites++;
            }
            foreach(var map in new[]{ScenarioKind.LosAngeles,ScenarioKind.London})
            {
                // Houses: own colour's house layer, inside the inset, outside every lot's one-tile ring, driveway to open land.
                var w=City(map,7);var profile=OriginalPlacementData.Get(map);w.Step(4000);
                w.PlaceableArea(out int x0,out int y0,out int x1,out int y1);
                for(int color=0;color<2;color++)for(int i=0;i<6;i++)
                {
                    var house=w.TrySpawnOriginalHouse(color,i==0?0:1,false);if(house==null)break;
                    var c=house.Cell;
                    Require(profile.HouseWeights[color][c.Y][c.X]!='.',"house on its colour's layer "+map+" "+c);
                    Require(c.X>=x0&&c.X<=x1&&c.Y>=y0&&c.Y<=y1,"house inside inset area");
                    Require(w.Buildings.Where(b=>!b.IsHouse).All(b=>!Near(b,c,1)),"no house in a lot's dead zone");
                    var outside=house.Access+TrafficWorld.Directions[house.DrivewayDirection];
                    Require(house.DrivewayDirection%2==0&&!w.Water[outside.X,outside.Y]&&!w.Blocked[outside.X,outside.Y]&&!w.Rails[outside.X,outside.Y]&&w.BuildingAt(outside)==null,"cardinal driveway to open land");
                }
                suites++;
            }
            {
                // Destinations: whole footprint on the colour's layer, clear of houses and lots by one tile; a new lot
                // pushes later destination entries to now + 10 s; a joined double lot does not.
                var w=City(ScenarioKind.LosAngeles,11);var profile=OriginalPlacementData.Get(ScenarioKind.LosAngeles);w.Step(2000);
                w.PendingSpawns.Clear();
                var later=new ScheduledSpawn{Type=0,Color=2,Time=w.Time+1,DemandMultiplier=1,Preference=1};w.PendingSpawns.Add(later);
                var before=w.Buildings.ToList();
                Require(w.TrySpawnPlannedDestination(new ScheduledSpawn{Type=0,Color=1,Grouping=2,Preference=1,DemandMultiplier=1,Time=w.Time}),"solo destination placed");
                var lot=w.Buildings.Last();
                for(int y=lot.Cell.Y;y<lot.Cell.Y+lot.Height;y++)for(int x=lot.Cell.X;x<lot.Cell.X+lot.Width;x++)
                    Require(profile.DestinationWeights[1][y][x]!='.',"lot tile on the colour's destination layer");
                var cells=new List<Cell>();for(int y=lot.Cell.Y;y<lot.Cell.Y+lot.Height;y++)for(int x=lot.Cell.X;x<lot.Cell.X+lot.Width;x++)cells.Add(new Cell(x,y));
                Require(before.All(b=>cells.All(c=>!Near(b,c,1))),"new lot clear of every house and lot by one tile");
                Require(Math.Abs(later.Time-(w.Time+10))<1e-9,"later destination entry waits 10 s");
                var plan=new ScheduledSpawn{Type=0,Color=3,Grouping=0,Preference=3,DemandMultiplier=1,Time=w.Time};
                Require(w.TrySpawnPlannedDestination(plan),"double lot placed");var shared=w.Buildings.Last();
                Require(shared.SharedLot&&(shared.Layout==0||shared.Layout==2),"ordinary double lots use two orientations");
                Building firstVacant()=>w.Buildings.FirstOrDefault(b=>b.SharedLot&&!b.IsStation&&b.DestinationSlot==0&&w.Buildings.Count(o=>!o.IsHouse&&o.CarparkId==b.CarparkId)==1);
                var vacant=firstVacant();Require(vacant!=null,"a vacant double lot exists");
                w.TrySpawnPlannedDestination(new ScheduledSpawn{Type=0,Color=vacant.Color,Grouping=0,Preference=3,DemandMultiplier=1,Time=w.Time});
                Require(w.Buildings.Count(b=>!b.IsHouse&&b.CarparkId==vacant.CarparkId)==1,"same colour never joins the first vacant lot");
                vacant=firstVacant();later.Time=w.Time+1;int count=w.Buildings.Count;int joinColor=(vacant.Color+1)%5;
                Require(w.TrySpawnPlannedDestination(new ScheduledSpawn{Type=0,Color=joinColor,Grouping=0,Preference=4,DemandMultiplier=1,Time=w.Time}),"join double lot");
                Require(w.Buildings.Count==count+1&&w.Buildings.Last().CarparkId==vacant.CarparkId&&Math.Abs(later.Time-(w.Time+1))<1e-9,"joins the first vacant lot without pushing later entries");
                var roll=new ScheduledSpawn{Type=0,Color=4,Grouping=0,Preference=0,DemandMultiplier=1,Time=w.Time};w.TrySpawnPlannedDestination(roll);
                Require(roll.Preference==1||roll.Preference==3,"no-preference entries keep their single roll");
                suites++;
            }
            {
                // A failing circle entry becomes an ordinary destination after more than five attempts; a failing double
                // entry becomes solo after more than four; destinations need no supporting house.
                var w=City(ScenarioKind.LosAngeles,5);w.PendingSpawns.Clear();
                var circle=new ScheduledSpawn{Type=0,Color=-1,Grouping=3,Attempts=6,DemandMultiplier=1,Time=w.Time};
                foreach(var b in w.Buildings.Where(b=>!b.IsHouse))b.UpgradeAt=w.Time;  // nothing left to upgrade
                w.PendingSpawns.Add(circle);w.ProcessOriginalPlan();
                Require(circle.Grouping==0&&circle.Attempts==1&&circle.Color>=0&&w.PendingSpawns.Contains(circle),"failed circle converts to a destination of an active colour");
                w.PendingSpawns.Clear();
                var houses=w.Buildings.Count(b=>b.IsHouse);var first=w.Buildings.First(b=>!b.IsHouse);
                int destinations=w.Buildings.Count(b=>!b.IsHouse);
                w.TrySpawnPlannedDestination(new ScheduledSpawn{Type=0,Color=(first.Color+1)%5,Grouping=0,Preference=1,DemandMultiplier=1,Time=w.Time});
                Require(w.Buildings.Count(b=>!b.IsHouse)==destinations+1&&w.Buildings.Count(b=>b.IsHouse)==houses,"a destination spawns alone, with no house of its own");
                w.PendingSpawns.Clear();
                var stubborn=new ScheduledSpawn{Type=0,Color=first.Color,Grouping=0,Preference=3,Attempts=5,DemandMultiplier=1,Time=w.Time};
                w.PendingSpawns.Add(stubborn);
                for(int y=0;y<TrafficWorld.Height;y++)for(int x=0;x<TrafficWorld.Width;x++)w.Blocked[x,y]=true; // nowhere to build
                w.ProcessOriginalPlan();
                Require(stubborn.Preference==1&&stubborn.Attempts==2,"double entry turns solo after more than four failures");
                suites++;
            }
            {
                // Supply distance is measured to the tile outside the lot's (top-left) driveway.
                var rules=Rules.ForVersion(GameVersion.OriginalReference);rules.EnableCityGrowth=false;
                var w=new TrafficWorld(1,false,rules);w.Reset(1,ScenarioKind.EmptyLab);
                var shop=w.SpawnBuilding(new Cell(20,10),0,false,0,0);var anchor=shop.Entrance+TrafficWorld.Directions[shop.DrivewayDirection];
                var home=w.SpawnBuilding(new Cell(anchor.X-12,anchor.Y),0,true,0);
                double expected=ReferenceCurves.Evaluate(OriginalGameplayTuning.HouseContribution,12)*OriginalGameplayTuning.HouseContributionMultiplier;
                Require(Math.Abs(w.HouseSupplyContribution(home,shop)-expected)<1e-12,"supply anchor outside the driveway");
                suites++;
            }
            return suites;
        }
    }
}
