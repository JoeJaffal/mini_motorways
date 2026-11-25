using System;
using System.Collections.Generic;
using System.Linq;
namespace MotorwaysSim
{
    // OriginalReference roundabout activation (AddRoundaboutEdit, ReleaseMothballedLanesProcess.CanPlannedRoundaboutHotswap,
    // VehicleMovementProcess hot-swap stop). A new roundabout is Planned: the roads it replaces are mothballed at once and
    // its own lanes do not exist yet. It becomes Active (hot-swaps) in the first step in which none of the replaced lanes,
    // nor the lanes leading into or out of them, has a vehicle on it or a vehicle committed to it (LaneModel.CanHotswap:
    // committed = the next two lanes of a path). Until then:
    // - new routes cannot pass through its five tiles: the old roads cost 100000 as mothballed lanes and the circle has no
    //   lanes, and dispatch never uses mothballed lanes. Our routes exclude the footprint instead (a route with no other way
    //   keeps its old lanes, as the original's last-resort mothballed path does);
    // - a car whose third path lane is a replaced lane, while its next two are not, stops at the end of its current lane
    //   so that it never commits to it (not when its current lane is a carpark lane);
    // - cars still on replaced lanes keep arbitrating at the old junction, whose road count is kept for that purpose.
    public sealed partial class TrafficWorld
    {
        readonly HashSet<Cell> plannedRoundaboutCells=new HashSet<Cell>();

        void RebuildPlannedRoundaboutCells()
        {
            plannedRoundaboutCells.Clear();
            foreach(var r in Roundabouts.Where(r=>r.Planned)){plannedRoundaboutCells.Add(r.Center);foreach(var c in r.Ring)plannedRoundaboutCells.Add(c);}
        }

        bool InPlannedRoundabout(Cell c)=>plannedRoundaboutCells.Count>0&&plannedRoundaboutCells.Contains(c);

        // A lane built before the circle that runs on its footprint, or reaches it through a link the circle removed.
        bool IsReplacedRoundaboutLane(Lane l)
        {
            if(plannedRoundaboutCells.Count==0||l==null||l.IsRoundabout||l.IsParking||l.IsMotorway)return false;
            if(plannedRoundaboutCells.Contains(l.Tile))return true;
            if(l.Next!=l.Tile&&plannedRoundaboutCells.Contains(l.Next)&&!Linked(l.Tile,l.Next))return true;
            if(l.Previous!=l.Tile&&plannedRoundaboutCells.Contains(l.Previous)&&!Linked(l.Previous,l.Tile))return true;
            return false;
        }

        // The road count of a footprint tile before the circle, for arbitration among cars still on the replaced lanes.
        bool TryPlannedChunkDegree(Cell tile,out int degree)
        {
            degree=0;if(plannedRoundaboutCells.Count==0||!plannedRoundaboutCells.Contains(tile))return false;
            foreach(var r in Roundabouts)if(r.Planned&&r.PlannedDegrees!=null&&r.PlannedDegrees.TryGetValue(tile,out degree))return true;
            return false;
        }

        bool HoldsReplacedLanes(Vehicle car)
        {
            if(!car.Moving)return false;
            for(int i=car.RouteIndex;i<Math.Min(car.Lanes.Count,car.RouteIndex+3);i++)if(IsReplacedRoundaboutLane(car.Lanes[i]))return true;
            return false;
        }

        // VehicleMovementProcess: path[0] and path[1] not about to hot-swap, path[2] about to -> stop before path[0].
        bool HotswapHold(Vehicle car)
        {
            if(plannedRoundaboutCells.Count==0||!car.Moving||car.CurrentLane.IsParking||car.RouteIndex+3>=car.Lanes.Count)return false;
            return !IsReplacedRoundaboutLane(car.Lanes[car.RouteIndex+1])&&!IsReplacedRoundaboutLane(car.Lanes[car.RouteIndex+2])&&
                IsReplacedRoundaboutLane(car.Lanes[car.RouteIndex+3]);
        }

        void ActivatePlannedRoundabouts()
        {
            if(plannedRoundaboutCells.Count==0)return;
            if(Cars.Any(HoldsReplacedLanes))return; // one footprint set: any planned circle still held keeps all planned
            foreach(var r in Roundabouts.Where(r=>r.Planned)){r.Planned=false;r.PlannedDegrees=null;}
            RebuildPlannedRoundaboutCells();Changed();
        }
    }
}
