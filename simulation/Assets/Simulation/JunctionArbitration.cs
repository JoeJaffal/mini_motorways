using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference junction entry arbitration, independently implemented from the rule description in
    // docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md (no original code).
    // Order: lane-count gate, red light, shove, traversing vehicles (shared-exit space, different-exit
    // release, geometry with green bypass), then inbound reservations among eligible candidates.
    // Not implemented because the description leaves them open: the effect of all-leader "pushing"
    // cycles, the stopped-candidate argument of the connection test, and the optional 45 s wait escape.
    public sealed partial class TrafficWorld
    {
        // Original: space must strictly exceed two vehicle lengths, found within five obstacle states.
        const int ExitSpaceStates=5;
        // Original pushing-cycle speed 0.2 world units/s = 0.1 tiles/s (2 world units per tile).
        const double PushingCycleSpeed=.1;
        // Our follower holds exactly FollowingGap behind a stopped leader, so the original's strict
        // "below the minimum gap" test cannot fire; a gap within this tolerance counts as tight.
        const double TightGapTolerance=.01;

        struct ObstacleRecord{public ObstacleKind Kind;public int Car;public double Distance;public int Blocker;public string BlockedLane;public Cell BlockedTile;}

        // A chunk with two or fewer lanes accepts entry without arbitration (before any light check).
        bool ChunkHasFewLanes(Cell tile)=>tile.X<0?!IsCrossingCorner(tile):Degree(tile)+Motorways.Count(m=>!m.PendingRemoval&&(m.Start==tile||m.End==tile))<=2;

        static bool IsImmediateNext(Vehicle car,Lane lane)=>car.RouteIndex+1<car.Lanes.Count&&ReferenceEquals(car.Lanes[car.RouteIndex+1],lane);

        // A chosen lane is committed when it is among the first two remaining planned lanes.
        // The original ring has a corner chunk between consecutive ring tiles, so a circulating car reaches a ring
        // tile's lane as its second path lane only from the previous ring tile; our ring lanes span both, so a
        // ring-to-ring target counts only as the immediate next lane.
        static bool Committed(Vehicle car,Lane lane)
        {
            for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+3);i++)
                if(ReferenceEquals(car.Lanes[i],lane))
                    return !(i==car.RouteIndex+2&&lane.IsRoundabout&&car.Lanes[i-1].IsRoundabout&&car.Lanes[i-1].Tile!=lane.Tile);
            return false;
        }

        bool MayEnterOriginal(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out string why,out int blocker)
        {
            why="";blocker=-1;
            if(lane.IsMotorway||lane.IsCorner&&!lane.IsJunction||ChunkHasFewLanes(lane.ChunkCell))return true;
            if(!LightAllowsEntry(lane)){why="Traffic light";return false;}
            if(car.Shoving&&car.ShovingLane==lane.Key&&IsImmediateNext(car,lane))return true;
            if(WaitedTooLong(car,lane))return true;
            if(!TraversingAllows(car,lane,snapshot,out blocker,out why))return false;
            if(!TryApproach(car,lane.ChunkCell,out _,out double ownDistance))return true;
            bool ownEligible=Committed(car,lane),ownRing=OnTargetRoundabout(car,lane);
            double ownRegistered=car.ApproachRegistered.TryGetValue(lane.Key,out var ownTime)?ownTime:Time;
            foreach(var other in snapshot)
            {
                if(other.Car.Id==car.Id||!TryApproach(other.Car,lane.ChunkCell,out var target,out double theirDistance))continue;
                // Original inbound order: crossing in front of a stopped candidate is allowed.
                bool stopped=other.Speed<.0005;
                if(!(lane.Incoming<8&&target.Incoming<8&&lane.ChunkCell==target.ChunkCell?ConnectionsIntersect(lane,target,stopped):Conflicts(lane,target))||!LightAllowsEntry(target))continue;
                bool theirShove=other.Car.Shoving&&other.Car.ShovingLane==target.Key&&IsImmediateNext(other.Car,target);
                // Ineligible candidates (uncommitted, or blocked by traffic inside the chunk) sort behind
                // every eligible one, so they never hold priority over an eligible entry.
                if(!theirShove&&!(Committed(other.Car,target)&&TraversingAllows(other.Car,target,snapshot,out _,out _)))continue;
                bool theirRing=OnTargetRoundabout(other.Car,lane);
                double theirRegistered=other.Car.ApproachRegistered.TryGetValue(target.Key,out var theirTime)?theirTime:Time;
                bool earlier=!ownEligible||theirShove||theirRing&&!ownRing||theirRing==ownRing&&
                    (theirDistance<ownDistance-1e-6||Math.Abs(theirDistance-ownDistance)<1e-6&&theirRegistered<ownRegistered||
                    Math.Abs(theirDistance-ownDistance)<1e-6&&theirRegistered==ownRegistered&&other.Car.Id<car.Id);
                if(earlier){why=lane.IsRoundabout?"Roundabout entry yield":"Approaching vehicle priority";blocker=other.Car.Id;return false;}
            }
            return true;
        }

        bool TraversingAllows(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out int blocker,out string why)
        {
            blocker=-1;why="";bool? space=null;bool green=Signals.ContainsKey(lane.ChunkCell)&&LightPermits(lane);
            foreach(var other in snapshot)
            {
                if(other.Car.Id==car.Id||other.Lane.IsMotorway||other.Lane.IsParking||other.Lane.ChunkCell!=lane.ChunkCell)continue;
                if(other.Index>=other.Car.Lanes.Count-1)continue; // no remaining path
                if(other.Lane.Outgoing==lane.Outgoing)
                {
                    // Same exit: the space test runs first and the near-exit release does not apply;
                    // the geometry check below still does.
                    space??=HasExitSpace(car,l=>l.ChunkCell==lane.ChunkCell&&!l.IsMotorway&&!l.IsParking);
                    if(!space.Value){blocker=other.Car.Id;why="Exit space";return false;}
                    // The original's connection test treats two lanes with the same exit as intersecting, so a
                    // car on a different lane merging into that exit blocks entry even when there is space.
                    if(!green&&other.Lane.Key!=lane.Key){blocker=other.Car.Id;why="Merging vehicle";return false;}
                }
                else if(other.Distance>other.Lane.Length-Rules.CarLength)continue;
                if(green)continue; // installed greenLightsIgnoreCollisions: bypasses geometry, not the space test
                if(Conflicts(lane,other.Lane)){blocker=other.Car.Id;why=lane.IsRoundabout?"Yield to circulating traffic":"Crossing vehicle";return false;}
            }
            return true;
        }

        // Feature MaximumWaitTimeAtIntersections is enabled in the installed DefaultConfig: a car committed to a chunk
        // lane for more than MaximumTimeToWaitAtIntersection (45 s) enters regardless of traffic and priority
        // (checked after the light and shove, before traversing vehicles).
        bool WaitedTooLong(Vehicle car,Lane lane)=>car.CommittedAt.TryGetValue(lane.Key,out var since)&&Time-since>Rules.MaximumIntersectionWait;

        Vehicle CarById(int id)=>id>=0&&id<Cars.Count&&Cars[id].Id==id?Cars[id]:Cars.Find(c=>c.Id==id);

        // Usable distance along the entering car's previous-tick obstacle chain.
        bool HasExitSpace(Vehicle car,Func<Lane,bool> inChunk)
        {
            double usable=0,needed=2*Rules.CarLength;var state=car;
            for(int i=0;i<ExitSpaceStates;i++)
            {
                switch(state.ObstacleState)
                {
                    case ObstacleKind.None:return true;
                    case ObstacleKind.RouteEnd:usable+=state.ObstacleDistance-Rules.CarLength;return usable>needed;
                    case ObstacleKind.BlockingJunction:usable+=state.ObstacleDistance;return usable>needed;
                    default:
                        var leader=CarById(state.ObstacleCar);if(leader==null)return usable>needed;
                        double distance=state.ObstacleDistance;
                        // A leader still inside the arbitrated chunk: discount its remaining distance there,
                        // keeping one vehicle length.
                        if(leader.Moving&&inChunk(leader.CurrentLane))
                            distance-=Math.Max(0,leader.CurrentLane.Length-leader.DistanceAlongLane-Rules.CarLength);
                        usable+=Math.Max(0,distance-Rules.CarLength);
                        if(usable>needed)return true;
                        state=leader;break;
                }
            }
            return false;
        }

        static ObstacleRecord NearestObstacle(int leader,double gap,double blockingDistance,int blocker,string blockedLane,double remaining,double lookahead)
        {
            var record=new ObstacleRecord{Kind=ObstacleKind.None,Car=-1,Blocker=-1,BlockedLane=""};double best=double.PositiveInfinity;
            if(leader>=0&&gap<best){best=gap;record=new ObstacleRecord{Kind=ObstacleKind.Leader,Car=leader,Distance=gap,Blocker=-1,BlockedLane=""};}
            if(!double.IsInfinity(blockingDistance)&&blockingDistance<best){best=blockingDistance;record=new ObstacleRecord{Kind=ObstacleKind.BlockingJunction,Car=-1,Distance=blockingDistance,Blocker=blocker,BlockedLane=blockedLane??""};}
            if(remaining<=lookahead&&remaining<best)record=new ObstacleRecord{Kind=ObstacleKind.RouteEnd,Car=-1,Distance=remaining,Blocker=-1,BlockedLane=""};
            return record;
        }

        // Follow blocking links; members of an actual cycle that are blocked by junction entry shove into
        // that junction lane next tick. All-leader cycles would become "pushing" relationships, whose
        // effect the description does not give; they are left unchanged.
        void MarkBlockingCycles(Dictionary<int,ObstacleRecord> records,Dictionary<int,double> nextSpeed)
        {
            var link=new Dictionary<int,(int to,bool junction)>();
            foreach(var item in records)
            {
                var r=item.Value;
                if(r.Kind==ObstacleKind.BlockingJunction&&r.Blocker>=0)link[item.Key]=(r.Blocker,true);
                else if(r.Kind==ObstacleKind.Leader&&nextSpeed[item.Key]<PushingCycleSpeed&&r.Distance-Rules.CarLength<Rules.FollowingGap+TightGapTolerance)
                    link[item.Key]=(r.Car,false);
            }
            var done=new HashSet<int>();
            foreach(int start in link.Keys)
            {
                if(done.Contains(start))continue;
                var path=new List<int>();var index=new Dictionary<int,int>();int at=start;
                while(link.ContainsKey(at)&&!done.Contains(at)&&!index.ContainsKey(at)){index[at]=path.Count;path.Add(at);at=link[at].to;}
                if(index.TryGetValue(at,out int first))
                {
                    var cycle=path.Skip(first).ToList();
                    foreach(int member in cycle)
                        if(link[member].junction){var car=CarById(member);car.Shoving=true;car.ShovingLane=records[member].BlockedLane;}
                }
                foreach(int member in path)done.Add(member);
            }
        }

        // Inbound registration at route assignment: each newly planned arbitrated lane is stamped with
        // game time plus the path's lane count; retained entries keep their stamp.
        void RegisterRoute(Vehicle car,bool keepExisting)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return;
            var planned=new HashSet<string>();
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++){var lane=car.Lanes[i];if(lane.IsJunction||lane.IsRoundabout||lane.IsParking)planned.Add(lane.Key);}
            if(keepExisting)
            {
                foreach(var key in car.ApproachRegistered.Keys.Where(k=>!planned.Contains(k)).ToArray())car.ApproachRegistered.Remove(key);
                var lanes=new HashSet<string>(car.Lanes.Skip(car.RouteIndex+1).Select(l=>l.Key));
                foreach(var key in car.CommittedAt.Keys.Where(k=>!lanes.Contains(k)).ToArray())car.CommittedAt.Remove(key);
            }
            else{car.ApproachRegistered.Clear();car.CommittedAt.Clear();}
            foreach(var key in planned)if(!car.ApproachRegistered.ContainsKey(key))car.ApproachRegistered[key]=Time+car.Lanes.Count;
            car.Shoving=false;car.ShovingLane="";NoteCommitments(car);
        }
    }
}
