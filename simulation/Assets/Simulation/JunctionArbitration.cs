using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference junction entry arbitration. First written from the rule description in
    // docs/training/simulator-repairs-2026-11-08/ORIGINAL_SPACE_CHECK_RULE_ANSWER.md, then checked against the decompiled
    // RoadChunkModel / VehicleMovementProcess (decisions 107, 112, 113, 122, 128). Order: lane-count gate, red light, shove,
    // 45 s wait escape, traversing vehicles (shared-exit space, different-exit release, geometry with green bypass), then
    // inbound reservations: eligible candidates first, ineligible ones behind in registration order. Blocking cycles start
    // from stuck vehicles; all-leader cycles push.
    public sealed partial class TrafficWorld
    {
        // Original: space must strictly exceed two vehicle lengths, found within five obstacle states.
        const int ExitSpaceStates=5;
        // Original pushing-cycle speed 0.2 world units/s = 0.1 tiles/s (2 world units per tile).
        const double PushingCycleSpeed=.1;

        struct ObstacleRecord{public ObstacleKind Kind;public int Car;public double Distance;public int Blocker;public string BlockedLane;public Cell BlockedTile;}

        // A chunk with two or fewer lanes accepts entry without arbitration (before any light check).
        // A crossing corner keeps arbitrating while a car still holds one of its junction lanes (an erased diagonal's
        // lanes stay until empty, as mothballed lanes do in the original).
        bool CornerStillCrossing(Cell code)=>Cars.Any(c=>c.Moving&&c.Lanes.Skip(c.RouteIndex).Take(3).Any(l=>l.IsJunction&&l.Corner==code));
        bool ChunkHasFewLanes(Cell tile)=>tile.X<0?!(IsCrossingCorner(tile)||CornerStillCrossing(tile)):TryPlannedChunkDegree(tile,out int planned)?planned<=2:Degree(tile)+Motorways.Count(m=>!m.PendingRemoval&&(m.Start==tile||m.End==tile))<=2;

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
                if(!(lane.Incoming<8&&target.Incoming<8&&lane.ChunkCell==target.ChunkCell?ConnectionsIntersect(lane,target,stopped):Conflicts(lane,target)))continue;
                bool theirShove=other.Car.Shoving&&other.Car.ShovingLane==target.Key&&IsImmediateNext(other.Car,target);
                // Ineligible candidates (uncommitted, held by a red light or blocked by traffic inside the chunk; a
                // shoving car is always eligible) sort behind every eligible one and keep roughly their registration
                // order, so they never hold priority over an eligible entry but do over a later ineligible one.
                if(!theirShove&&!(Committed(other.Car,target)&&LightAllowsEntry(target)&&TraversingAllows(other.Car,target,snapshot,out _,out _)))
                {
                    if(ownEligible||!RegisteredBefore(other.Car,target.Key,car,lane.Key))continue;
                    why=lane.IsRoundabout?"Roundabout entry yield":"Approaching vehicle priority";blocker=other.Car.Id;return false;
                }
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
                    case ObstacleKind.RouteEnd:
                        // Original Target case: targetDistanceAlongLastLane - distanceAlongLane - vehicle length, taken
                        // from the vehicle's current lane even when its target lies on a later lane (no floor at zero).
                        if(Rules.Version==GameVersion.OriginalReference&&state.Moving&&state.RouteIndex<TargetLaneIndex(state))
                            usable+=state.Lanes[TargetLaneIndex(state)].Length-state.DistanceAlongLane-Rules.CarLength;
                        else usable+=state.ObstacleDistance-Rules.CarLength;
                        return usable>needed;
                    case ObstacleKind.BlockingJunction:usable+=state.ObstacleDistance;return usable>needed;
                    default:
                        var leader=CarById(state.ObstacleCar);if(leader==null)return usable>needed;
                        double distance=state.ObstacleDistance;
                        // Original DoesVehicleHaveSpace: a leader on a lane of the chunk being entered has that lane's
                        // length less one vehicle length taken off its distance, wherever on the lane it is.
                        if(leader.Moving&&inChunk(leader.CurrentLane))
                            distance-=leader.CurrentLane.Length-Rules.CarLength;
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

        // Original VehicleMovementProcess blocking cycles. Stuck vehicles are those refused entry to the chunk of their
        // immediate next lane (path[0]) with no leader on their own lane, and those whose nearest obstacle is a leader
        // less than MinimumGap (0.1 world units) ahead by position (the two practically overlap) while their next speed
        // is below minSpeedBeforePushingCycle (0.2 world units/s). From each stuck vehicle the chain of blocking vehicles
        // is followed: a leader (at any distance) or, for a car refused at its immediate next chunk, the vehicle that
        // refuses it; a junction further ahead has no blocking vehicle, so the chain ends there. A chain that closes on
        // itself is a cycle: members refused at a junction shove into it next tick; if every member follows a leader they
        // push into their leaders (PushingInto, see ApplyPushing).
        bool RefusedAtNextLane(int id,ObstacleRecord r)
        {
            if(r.Kind!=ObstacleKind.BlockingJunction)return false;var car=CarById(id);
            return car!=null&&car.Moving&&car.RouteIndex+1<car.Lanes.Count&&car.Lanes[car.RouteIndex+1].Key==r.BlockedLane;
        }
        void MarkBlockingCycles(Dictionary<int,ObstacleRecord> records,Dictionary<int,double> nextSpeed)
        {
            var checkedThisTick=new HashSet<int>();
            foreach(var item in records)
            {
                var r=item.Value;
                bool stuck=RefusedAtNextLane(item.Key,r)||r.Kind==ObstacleKind.Leader&&nextSpeed[item.Key]<PushingCycleSpeed&&r.Distance<Rules.FollowingGap;
                if(!stuck)continue;
                var chain=new List<int>();int at=item.Key;
                while(at>=0)
                {
                    if(checkedThisTick.Contains(at))
                    {
                        int first=chain.IndexOf(at);
                        if(first>=0)BreakCycle(chain.Skip(first).ToList(),records);
                        break;
                    }
                    chain.Add(at);checkedThisTick.Add(at);
                    if(!records.TryGetValue(at,out var link))break;
                    at=link.Kind==ObstacleKind.Leader?link.Car:RefusedAtNextLane(at,link)?link.Blocker:-1;
                }
            }
        }
        void BreakCycle(List<int> cycle,Dictionary<int,ObstacleRecord> records)
        {
            if(cycle.Any(m=>records[m].Kind==ObstacleKind.BlockingJunction))
            {
                foreach(int member in cycle)
                    if(records[member].Kind==ObstacleKind.BlockingJunction){var car=CarById(member);car.Shoving=true;car.ShovingLane=records[member].BlockedLane;}
            }
            else if(cycle.All(m=>records[m].Kind==ObstacleKind.Leader))
            {foreach(int member in cycle){var car=CarById(member);if(car!=null)car.PushingInto=records[member].Car;}}
        }
        // Original pushing: while a car's nearest obstacle is still the leader it pushes into, it takes the leader's speed
        // as at least minSpeedBeforePushingCycle and the gap as at least a vehicle length plus two minimum gaps, so it
        // creeps on. The cycle breaks (every member stops pushing) when that leader moves faster on its own or the car's
        // obstacle changes.
        bool ApplyPushing(Vehicle car,int leaderId,bool leaderNearest,ref double gap,ref double leaderSpeed,HashSet<int> broken)
        {
            if(car.PushingInto<0)return false;
            if(!leaderNearest||leaderId!=car.PushingInto){broken.Add(car.Id);return false;}
            if(leaderSpeed>PushingCycleSpeed)broken.Add(car.Id);
            leaderSpeed=Math.Max(leaderSpeed,PushingCycleSpeed);gap=Math.Max(gap,Rules.CarLength+2*Rules.FollowingGap);
            return true;
        }
        void BreakPushingCycles(HashSet<int> broken)
        {
            foreach(int id in broken)
            {
                var car=CarById(id);
                while(car!=null&&car.PushingInto>=0){int next=car.PushingInto;car.PushingInto=-1;car=CarById(next);}
            }
        }

        // Inbound registration at route assignment (original AssignPath -> AddInboundVehicle): each newly planned
        // arbitrated lane is stamped with game time plus its position in the path (1 for the next lane); retained
        // entries (the unchanged start of a re-planned path) keep their stamp.
        long registrationSequence;
        bool RegisteredBefore(Vehicle a,string laneA,Vehicle b,string laneB)=>
            a.RegisteredOrder.TryGetValue(laneA,out long x)&&b.RegisteredOrder.TryGetValue(laneB,out long y)&&x<y;
        internal void RegisterRouteForChecks(Vehicle car)=>RegisterRoute(car,false); // fixtures that place cars directly
        void RegisterRoute(Vehicle car,bool keepExisting)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return;
            var planned=new Dictionary<string,int>();
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++){var lane=car.Lanes[i];if((lane.IsJunction||lane.IsRoundabout||lane.IsParking)&&!planned.ContainsKey(lane.Key))planned[lane.Key]=i-car.RouteIndex;}
            if(keepExisting)
            {
                // Original AssignPath keeps the registrations along the unchanged start of the new path and re-registers
                // every lane from the first difference (fresh stamp, back of the inbound list, new commitment time).
                var order=planned.OrderBy(p=>p.Value).Select(p=>p.Key).ToList();
                var old=car.RegisteredPath.Where(k=>car.ApproachRegistered.ContainsKey(k)).ToList();
                int common=0;while(common<old.Count&&common<order.Count&&old[common]==order[common])common++;
                var kept=new HashSet<string>(order.Take(common));
                foreach(var key in car.ApproachRegistered.Keys.Where(k=>!kept.Contains(k)).ToArray()){car.ApproachRegistered.Remove(key);car.CommittedAt.Remove(key);}
                var lanes=new HashSet<string>(car.Lanes.Skip(car.RouteIndex+1).Select(l=>l.Key));
                foreach(var key in car.CommittedAt.Keys.Where(k=>!lanes.Contains(k)).ToArray())car.CommittedAt.Remove(key);
            }
            else{car.ApproachRegistered.Clear();car.CommittedAt.Clear();}
            foreach(var item in planned.OrderBy(p=>p.Value))if(!car.ApproachRegistered.ContainsKey(item.Key)){car.ApproachRegistered[item.Key]=Time+item.Value;car.RegisteredOrder[item.Key]=++registrationSequence;}
            car.RegisteredPath=planned.OrderBy(p=>p.Value).Select(p=>p.Key).ToList();
            // Original AssignPath keeps shoving and pushing through a re-plan; only a new trip starts clear (decision 116).
            if(!keepExisting){car.Shoving=false;car.ShovingLane="";car.PushingInto=-1;}
            NoteCommitments(car);
        }
    }
}
