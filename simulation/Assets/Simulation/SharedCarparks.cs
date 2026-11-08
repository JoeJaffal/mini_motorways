using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        double doubleLotProbability=.3;
        public bool SameCarpark(int a,int b)=>a>=0&&b>=0&&!Buildings[a].IsHouse&&!Buildings[b].IsHouse&&Buildings[a].CarparkId==Buildings[b].CarparkId;
        public bool HasAccess(Building b,Cell c)=>b.IsHouse?b.Cell==c:b.Entrances.Length==0?b.Access==c:Array.IndexOf(b.Entrances,c)>=0;
        public int AccessDirection(Building b,Cell c)
        {int i=Array.IndexOf(b.Entrances,c);return i<0?b.DrivewayDirection:b.EntranceDirections[i];}
        public IEnumerable<Cell> Accesses(Building b)=>b.IsHouse||b.Entrances.Length==0?new[]{b.Access}:b.Entrances;
        public List<Cell> BestRouteTo(Cell start,Building shop,bool retired=false)
        {
            List<Cell> best=new List<Cell>();double cost=double.PositiveInfinity;
            foreach(var entry in Accesses(shop)){var path=FindRoute(start,entry,retired);if(path.Count<2)continue;double value=RouteCost(path);if(value<cost){best=path;cost=value;}}
            return best;
        }
        public List<Cell> BestPotentialRoute(Cell start,Building shop)
        {
            List<Cell> best=new List<Cell>();double cost=double.PositiveInfinity;
            foreach(var entry in Accesses(shop)){var path=PotentialRoute(start,entry);if(path.Count<2)continue;double value=0;for(int i=1;i<path.Count;i++)value+=Distance(path[i-1],path[i]);if(value<cost){best=path;cost=value;}}
            return best;
        }
        Cell LotCell(Cell origin,int layout,int along,int across,int length)
        {
            if(layout<2)return new Cell(origin.X+along,origin.Y+(layout==1?2-across:across));
            return new Cell(origin.X+(layout==3?across:2-across),origin.Y+along);
        }
        public Building SpawnSharedCarpark(Cell origin,int color,int layout=0,bool station=false)
        {
            if(Rules.Version!=GameVersion.OriginalReference||color<0||color>=Map.BaseDemand.Length||layout<0||layout>3)return null;
            int width=layout<2?4:3,height=layout<2?3:4;
            var platform=station?Enumerable.Range(0,4).Select(i=>LotCell(origin,layout,i,0,4)).ToArray():new Cell[0];
            if(station&&platform.Any(c=>!InBounds(c)||!Rails[c.X,c.Y]))return null;
            for(int y=origin.Y;y<origin.Y+height;y++)for(int x=origin.X;x<origin.X+width;x++)
            {
                var c=new Cell(x,y);
                if(!IsPlayable(c)||Water[x,y]||Blocked[x,y]||BuildingAt(c)!=null||Tile(c)!=Infrastructure.None||IsMotorwayEndpoint(c,true)||
                    Unzoneable[x,y]&&!platform.Contains(c)||Buildings.Any(b=>Accesses(b).Any(e=>e+Directions[AccessDirection(b,e)]==c)))return null;
            }
            var entrances=new[]{LotCell(origin,layout,0,2,4),LotCell(origin,layout,3,2,4)};
            var directions=layout<2?new[]{4,0}:new[]{6,2};
            for(int i=0;i<2;i++)
            {
                var outside=entrances[i]+Directions[directions[i]];
                if(!IsPlayable(outside)||Water[outside.X,outside.Y]||Blocked[outside.X,outside.Y]||BuildingAt(outside)!=null||RoundaboutAt(outside)!=null)return null;
            }
            var shop=new Building{Id=Buildings.Count,CarparkId=Buildings.Count,Cell=origin,Color=color,Width=width,Height=height,
                Layout=layout,SharedLot=true,IsStation=station,Entrance=entrances[0],DrivewayDirection=directions[0],Entrances=entrances,EntranceDirections=directions,
                Parking=Enumerable.Repeat(-1,9).ToArray(),Platform=platform,SpawnTime=Time,SpawnGraceUntil=Time+Rules.ConstructionGraceSeconds,
                DemandCountdown=Rules.FirstDemandDelay,NextDemand=Time+Rules.FirstDemandDelay};
            Buildings.Add(shop);for(int i=0;i<2;i++)AttachNativeDrivewaysAt(entrances[i]+Directions[directions[i]]);
            Changed();return shop;
        }
        public Building JoinSharedCarpark(int id,int color)
        {
            if(Rules.Version!=GameVersion.OriginalReference||id<0||id>=Buildings.Count||color<0||color>=Map.BaseDemand.Length)return null;
            var first=Buildings[id];if(!first.SharedLot||Buildings.Count(b=>!b.IsHouse&&b.CarparkId==first.CarparkId)>=2||Buildings.Any(b=>!b.IsHouse&&b.CarparkId==first.CarparkId&&b.Color==color))return null;
            var shop=new Building{Id=Buildings.Count,CarparkId=first.CarparkId,DestinationSlot=1,Cell=first.Cell,Color=color,Width=first.Width,Height=first.Height,
                Layout=first.Layout,SharedLot=true,IsStation=first.IsStation,Entrance=first.Entrance,DrivewayDirection=first.DrivewayDirection,
                Entrances=first.Entrances,EntranceDirections=first.EntranceDirections,Parking=first.Parking,Platform=first.Platform,
                SpawnTime=Time,SpawnGraceUntil=Time+Rules.ConstructionGraceSeconds,DemandCountdown=Rules.FirstDemandDelay,NextDemand=Time+Rules.FirstDemandDelay};
            Buildings.Add(shop);InitializeDestinationDemand(shop);Changed();return shop;
        }
        bool CompleteSupply(Building shop)
        {
            bool supply=Buildings.Any(b=>b.IsHouse&&b.Color==shop.Color&&BestPotentialRoute(b.Access,shop).Count>1)||TrySpawnHouse(shop);
            if(!supply){DiscardDestination(shop);return false;}RefreshFeasibility(shop);return true;
        }
        void DiscardDestination(Building shop)
        {
            if(shop.DestinationSlot==0)foreach(var entry in Accesses(shop))
                for(int d=0;d<8;d++)if((Connections[entry.X,entry.Y]&(1<<d))!=0)Unlink(entry,entry+Directions[d]);
            Buildings.Remove(shop);Changed();
        }
        bool TrySpawnPlannedDestination(ScheduledSpawn plan)
        {
            int color=plan.Color<0?random.Next(Map.BaseDemand.Length):plan.Color;int preference=plan.Preference;
            if(preference==0){if(random.NextDouble()<=doubleLotProbability){preference=3;doubleLotProbability=.3;}else doubleLotProbability+=.05;}
            bool station=preference==5||preference==6||preference==8;
            bool shared=station||preference==2||preference==3||preference==4||preference==7;
            if(shared&&preference!=7&&preference!=8)
            {
                foreach(var first in Buildings.Where(b=>b.SharedLot&&b.DestinationSlot==0&&b.IsStation==station).ToArray())
                {var joined=JoinSharedCarpark(first.Id,color);if(joined!=null&&CompleteSupply(joined)){joined.PlannedDemandMultiplier=plan.DemandMultiplier;return true;}}
            }
            if(!shared)return TrySpawnShop(color);
            var candidates=Enumerable.Range(0,Width*Height).Select(k=>new Cell(k%Width,k/Width)).ToList();Shuffle(candidates);
            foreach(var cell in candidates)
            {
                if(station?!Map.StationZone.Any(k=>k%Width>=cell.X&&k%Width<cell.X+4&&k/Width>=cell.Y&&k/Width<cell.Y+4):Array.IndexOf(Map.ShopZones[color],cell.Y*Width+cell.X)<0)continue;
                int firstLayout=random.Next(4);
                for(int i=0;i<4;i++)
                {var shop=SpawnSharedCarpark(cell,color,(firstLayout+i)%4,station);if(shop!=null&&CompleteSupply(shop)){shop.PlannedDemandMultiplier=plan.DemandMultiplier;return true;}}
            }
            // Original falls back after repeated failed double-lot placements; never turn a station into a normal destination.
            return !station&&plan.Attempts>10&&TrySpawnShop(color);
        }
        public Point DestinationCenter(Building shop)=>LayoutPoint(shop,1+2*shop.DestinationSlot,1);
    }
}
