using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference carpark lanes as arbitrated chunks, independently implemented from the description in
    // docs/training/simulator-repairs-2026-11-08/ORIGINAL_SIGNALS_CARPARKS_ANSWER.md (B1-B4; no original code).
    // Chunks: each entrance end holds its entrance, exit and turn-around lanes; each bay has an outer and an inner
    // circulation chunk (through, bay-entry and bay-exit lanes) and a bay chunk. Entry follows the same order as
    // road junctions: lane-count gate, shove, traversing vehicles (shared-exit space test, different-exit release,
    // geometry), then committed inbound candidates by route distance and registration time.
    public sealed partial class TrafficWorld
    {
        static string ParkingChunkName(string key)
        {
            if(key.StartsWith("entrance:")||key.StartsWith("exit:")||key.StartsWith("turn-"))return key.EndsWith("first")?"end-first":"end-last";
            string[] parts=key.Split(':');
            if(parts[0]=="outer"||parts[0]=="bay-outer-in"||parts[0]=="bay-outer-out")return "outer-"+parts[1];
            if(parts[0]=="inner"||parts[0]=="bay-inner-in"||parts[0]=="bay-inner-out")return "inner-"+parts[1];
            if(parts[0]=="bay-park"||parts[0]=="bay-leave")return "bay-"+parts[1];
            return key;
        }

        int ParkingChunkLaneCount(Lane lane)
        {
            var lot=Buildings.Find(b=>!b.IsHouse&&b.CarparkId==lane.CarparkId);if(lot==null)return 0;
            bool left=false,right=false;
            foreach(var access in Accesses(lot)){int d=AccessDirection(lot,access);if(d==4||d==6)left=true;else right=true;}
            string name=lane.Chunk.Substring(lane.Chunk.LastIndexOf(':')+1);
            if(name=="end-first")return (left?2:0)+1;
            if(name=="end-last")return (right?2:0)+1;
            if(name.StartsWith("bay-"))return left&&right?4:2;
            return 3;
        }

        static bool SameEnd(Lane a,Lane b)=>Point.Distance(a.Samples[a.Samples.Length-1],b.Samples[b.Samples.Length-1])<1e-6;

        bool ParkingTraversingAllows(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out int blocker,out string why)
        {
            blocker=-1;why="";bool? space=null;
            foreach(var other in snapshot)
            {
                if(other.Car.Id==car.Id||!other.Lane.IsParking||other.Lane.Chunk!=lane.Chunk)continue;
                if(other.Index>=other.Car.Lanes.Count-1)continue; // no remaining path
                if(SameEnd(other.Lane,lane))
                {
                    space??=HasExitSpace(car,l=>l.IsParking&&l.Chunk==lane.Chunk);
                    if(!space.Value){blocker=other.Car.Id;why="Exit space";return false;}
                    // Same exit counts as intersecting in the original's connection test (see TraversingAllows).
                    if(other.Lane.Key!=lane.Key){blocker=other.Car.Id;why="Merging vehicle";return false;}
                }
                else if(other.Distance>other.Lane.Length-Rules.CarLength)continue;
                if(Conflicts(lane,other.Lane)){blocker=other.Car.Id;why="Carpark lane conflict";return false;}
            }
            return true;
        }

        // The committed chosen lane in a carpark chunk (among the first two remaining planned lanes) and its route distance.
        static bool ParkingTarget(Vehicle car,string chunk,out Lane target,out double distance)
        {
            target=null;distance=car.Moving?car.CurrentLane.Length-car.DistanceAlongLane:0;if(!car.Moving)return false;
            for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+3);i++)
            {
                if(car.Lanes[i].IsParking&&car.Lanes[i].Chunk==chunk){target=car.Lanes[i];return true;}
                distance+=car.Lanes[i].Length;
            }
            return false;
        }

        bool MayEnterParkingOriginal(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out string why,out int blocker)
        {
            why="";blocker=-1;
            if(ParkingChunkLaneCount(lane)<=2)return true;
            if(car.Shoving&&car.ShovingLane==lane.Key&&IsImmediateNext(car,lane))return true;
            if(!ParkingTraversingAllows(car,lane,snapshot,out blocker,out why))return false;
            if(!ParkingTarget(car,lane.Chunk,out var own,out double ownDistance)||!ReferenceEquals(own,lane))return true;
            double ownRegistered=car.ApproachRegistered.TryGetValue(lane.Key,out var ownTime)?ownTime:Time;
            foreach(var other in snapshot)
            {
                if(other.Car.Id==car.Id||!ParkingTarget(other.Car,lane.Chunk,out var target,out double theirDistance))continue;
                if(!Conflicts(lane,target))continue;
                bool theirShove=other.Car.Shoving&&other.Car.ShovingLane==target.Key&&IsImmediateNext(other.Car,target);
                if(!theirShove&&!ParkingTraversingAllows(other.Car,target,snapshot,out _,out _))continue;
                double theirRegistered=other.Car.ApproachRegistered.TryGetValue(target.Key,out var theirTime)?theirTime:Time;
                bool earlier=theirShove||theirDistance<ownDistance-1e-6||Math.Abs(theirDistance-ownDistance)<1e-6&&
                    (theirRegistered<ownRegistered||theirRegistered==ownRegistered&&other.Car.Id<car.Id);
                if(earlier){why="Carpark merge priority";blocker=other.Car.Id;return false;}
            }
            return true;
        }
    }
}
