using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // The original has no whole-entrance owner gate; carpark lanes use chunk arbitration (CarparkArbitration.cs).
        // The engineered gate (decisions 074/076) only compensated for our extra body-clearance check, which the
        // original also lacks; with both removed the entrance runs on ordinary arbitration (decision 079).
        static readonly bool CarparkApproachGate=false;
        readonly Dictionary<(int,Cell),int> carparkThroats=new Dictionary<(int,Cell),int>();
        bool TryCarparkGate(Vehicle car,Lane lane,out int lot,out Cell access,out double distance)
        {
            lot=-1;access=new Cell();distance=0;if(car.ShopId<0||!car.Moving)return false;
            bool connector=lane.IsParking&&(lane.Key.Contains(":entrance:")||lane.Key.Contains(":exit:"));
            bool finalRoad=car.Stage==TripStage.Outbound&&ReferenceEquals(lane,car.Lanes.Last())&&!lane.IsParking;
            // A car passing through a shared lot is gated at the same point as an arriving car: the start
            // of the outside road lane that leads into the entrance connector.
            Lane entrance=null;
            if(!connector&&!finalRoad&&!lane.IsParking)
            {
                int index=car.Lanes.IndexOf(lane);
                if(index>=0&&index+1<car.Lanes.Count&&car.Lanes[index+1].IsParking&&car.Lanes[index+1].Key.Contains(":entrance:"))entrance=car.Lanes[index+1];
            }
            if(!connector&&!finalRoad&&entrance==null)return false;
            lot=connector?lane.CarparkId:entrance!=null?entrance.CarparkId:Buildings[car.ShopId].CarparkId;
            access=connector?lane.Tile:entrance!=null?entrance.Tile:car.DestinationAccess;
            // Reserve the outside approach before its turn starts, not at the
            // parcel boundary where a waiting car can obstruct an exiting turn.
            if(ReferenceEquals(lane,car.CurrentLane)){distance=-car.DistanceAlongLane;return true;}
            distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)
            {
                if(ReferenceEquals(car.Lanes[i],lane))return true;
                distance+=car.Lanes[i].Length;
            }
            return false;
        }
        double NearestCarparkGate(Vehicle car,int lot,Cell access)
        {
            double nearest=double.PositiveInfinity;
            for(int i=car.RouteIndex;i<car.Lanes.Count;i++)
                if(TryCarparkGate(car,car.Lanes[i],out int candidate,out var point,out double distance)&&candidate==lot&&point==access)
                    nearest=Math.Min(nearest,distance);
            return nearest;
        }
        bool CarparkThroatAllows(Vehicle car,Lane lane)
        {
            if(!TryCarparkGate(car,lane,out int lot,out var access,out double distance)||distance>Rules.CarLength+.3)return true;
            var key=(lot,access);if(carparkThroats.TryGetValue(key,out int owner))return owner==car.Id;
            // Every requester is ranked by its nearest gate point, which for arriving and passing-through
            // cars alike is the start of the outside approach lane (one distance measure, as the original).
            Vehicle nearest=car;double nearestDistance=distance;
            foreach(var other in Cars.Where(v=>v.Id!=car.Id&&v.Moving&&!RedBeforeGate(v,lot,access)))
            {
                double otherDistance=NearestCarparkGate(other,lot,access);
                if(otherDistance<nearestDistance-1e-8||Math.Abs(otherDistance-nearestDistance)<1e-8&&other.Id<nearest.Id)
                {nearest=other;nearestDistance=otherDistance;}
            }
            carparkThroats[key]=nearest.Id;return nearest.Id==car.Id;
        }
        // As in the original's entry eligibility, a car held by a red light before it reaches its gate lane is not
        // eligible to take or keep the gate (it would otherwise lock the car park for the green-side queue).
        bool RedBeforeGate(Vehicle car,int lot,Cell access)
        {
            if(Rules.Version!=GameVersion.OriginalReference||!car.Moving)return false;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)
            {
                var lane=car.Lanes[i];
                if(!lane.IsParking&&!lane.IsMotorway&&Signals.ContainsKey(lane.Tile)&&!LightAllowsEntry(lane))return true;
                if(TryCarparkGate(car,lane,out int candidate,out var point,out _)&&candidate==lot&&point==access)return false;
            }
            return false;
        }
        int CarparkGateOwner(Vehicle car,Lane lane)
        {
            if(!TryCarparkGate(car,lane,out int lot,out var access,out _))return -1;
            return carparkThroats.TryGetValue((lot,access),out int owner)&&owner!=car.Id?owner:-1;
        }
        void ReleaseCarparkThroats()
        {
            foreach(var item in carparkThroats.ToArray())
            {
                var car=Cars.Find(c=>c.Id==item.Value);bool keep=false;
                if(car!=null&&car.ShopId>=0&&car.Moving)
                {
                    var lot=Buildings[item.Key.Item1];var access=item.Key.Item2;
                    bool onConnector=car.CurrentLane.IsParking&&car.CurrentLane.CarparkId==lot.CarparkId&&car.CurrentLane.Tile==access&&
                        (car.CurrentLane.Key.Contains(":entrance:")||car.CurrentLane.Key.Contains(":exit:"));
                    double distance=NearestCarparkGate(car,lot.CarparkId,access);
                    bool approaching=distance>=0&&distance<=Rules.CarLength+.3;
                    bool clearing=PhysicalCarpark(car)==lot.CarparkId&&
                        (Point.Distance(car.Position,ParkingAccessPoint(lot,access,true))<Rules.CarLength+.1||
                         Point.Distance(car.Position,ParkingAccessPoint(lot,access,false))<Rules.CarLength+.1);
                    bool onApproach=!car.CurrentLane.IsParking&&TryCarparkGate(car,car.CurrentLane,out int approachLot,out var approachAccess,out _)&&
                        approachLot==lot.CarparkId&&approachAccess==access;
                    keep=onConnector||onApproach||clearing||approaching&&!RedBeforeGate(car,lot.CarparkId,access);
                }
                if(!keep)carparkThroats.Remove(item.Key);
            }
        }
        void UpdateSignalPairs(SignalState signal)
        {
            int remaining=Connections[signal.Cell.X,signal.Cell.Y];
            // Committed lanes still need a signal phase after their surface
            // connection is erased, until its retirement actually clears.
            foreach(var edge in retiredConnectionConcrete.Keys)
            {
                if(edge.Item1==signal.Cell)remaining|=1<<Direction(signal.Cell,edge.Item2);
                else if(edge.Item2==signal.Cell)remaining|=1<<Direction(signal.Cell,edge.Item1);
            }
            var masks=new List<int>();
            // The original (TrafficLightModel.CalculatePairs) scans directions starting at North (our 6).
            int first=Rules.Version==GameVersion.OriginalReference?6:0;
            for(int k=0;k<4;k++){int d=(first+k)%8,o=(d+4)%8;if((remaining&(1<<d))!=0&&(remaining&(1<<o))!=0)
            {int mask=(1<<d)|(1<<o);masks.Add(mask);remaining&=~mask;}}
            for(int k=0;k<8;k++)
            {
                int d=(first+k)%8;
                if((remaining&(1<<d))==0)continue;
                int a=(d+3)%8,b=(d+5)%8;
                if((remaining&(1<<a))!=0&&(remaining&(1<<b))!=0)continue;
                int pair=(remaining&(1<<a))!=0?a:(remaining&(1<<b))!=0?b:-1;
                if(pair>=0){int mask=(1<<d)|(1<<pair);masks.Add(mask);remaining&=~mask;}
            }
            for(int k=0;k<8;k++){int d=(first+k)%8;if((remaining&(1<<d))!=0)masks.Add(1<<d);}
            signal.Pairs=masks;
            if(!masks.Contains(signal.ActivePair))
            {
                if(Rules.Version==GameVersion.OriginalReference&&masks.Count>0)
                {
                    // Original: the active pair is gone, so rotate at once (no amber) to the best-weighted pair, or the
                    // first one when nothing waits, and restart the timer.
                    var candidates=SignalCandidates(signal.Cell);int best=masks[0];double weight=0;
                    if(candidates.Count>0)foreach(int pair in masks){double w=PairWeight(signal,pair,candidates);if(w>weight){best=pair;weight=w;}}
                    signal.ActivePair=best;signal.Amber=false;signal.Elapsed=0;
                }
                else signal.ActivePair=masks.Count==0?0:masks[0];
            }
        }

        public int SignalPhase(Cell c)=>Signals.TryGetValue(c,out var s)?s.Amber?-1:(s.ActivePair&17)!=0?0:1:-1;
        public bool SignalAllows(Cell cell,int incoming)
        {
            if(!Signals.TryGetValue(cell,out var s))return true;
            int approach=(incoming+4)%8;return !s.Amber&&(s.ActivePair&(1<<approach))!=0;
        }

        void UpdateSignals()
        {
            if(Rules.Version==GameVersion.OriginalReference){UpdateSignalsOriginal();return;}
            foreach(var signal in Signals.Values)
            {
                signal.Elapsed+=Rules.TickSeconds;
                if(signal.Pairs.Count==0)UpdateSignalPairs(signal);
                if(signal.Amber)
                {
                    if(signal.Elapsed>=Rules.SignalAmberSeconds)
                    {signal.ActivePair=BestSignalPair(signal,true);signal.Amber=false;signal.Elapsed=0;}
                    continue;
                }
                if(signal.Elapsed<(signal.Overtime?Rules.SignalOvertimeSeconds:Rules.SignalGreenSeconds))continue;
                int nearby=0;
                foreach(var car in Cars)
                {
                    if(!TryApproach(car,signal.Cell,out var lane,out double distance)||distance>Rules.SignalNearbyDistance)continue;
                    if((signal.ActivePair&(1<<((lane.Incoming+4)%8)))!=0)nearby++;
                }
                int best=BestSignalPair(signal,false);
                if(best!=signal.ActivePair&&(nearby==0||nearby>=Rules.SignalMinimumNearbyCars))
                {signal.Amber=true;signal.Overtime=false;}
                else signal.Overtime=true;
                signal.Elapsed=0;
            }
        }
        int BestSignalPair(SignalState signal,bool excludeCurrent)
        {
            int best=signal.ActivePair;double weight=-1;
            foreach(int pair in signal.Pairs)
            {
                if(excludeCurrent&&pair==signal.ActivePair)continue;
                double sum=0;
                foreach(var car in Cars)
                {
                    if(!TryApproach(car,signal.Cell,out var lane,out double distance))continue;
                    if((pair&(1<<((lane.Incoming+4)%8)))==0)continue;
                    double wait=Math.Min(1,car.Waiting/Rules.SignalMaxWaitingWeightSeconds);
                    double value=1+wait*wait;
                    if(car.Obstacle=="Queue ahead")value*=.1;
                    if(car.Stage==TripStage.LeavingParking)value*=2;
                    if(PendingRemoval[lane.Tile.X,lane.Tile.Y])value*=2;
                    sum+=value;
                }
                if(sum>weight){best=pair;weight=sum;}
            }
            return weight<=0?signal.ActivePair:best;
        }

        bool TryApproach(Vehicle car,Cell junction,out Lane lane,out double distance)
        {
            lane=null;distance=0;if(!car.Moving)return false;
            distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++)
            {
                if(car.Lanes[i].Tile==junction){lane=car.Lanes[i];return true;}
                distance+=car.Lanes[i].Length;if(distance>Rules.LookaheadDistance)return false;
            }
            return false;
        }

        readonly Dictionary<string,bool> conflictCache=new Dictionary<string,bool>();
        internal bool ConflictsPublic(Lane a,Lane b)=>Conflicts(a,b); // read-only, for checks
        bool Conflicts(Lane a,Lane b)
        {
            if(a.IsMotorway||b.IsMotorway)return false;
            if(a.Key==b.Key)return false;
            if(a.IsParking&&b.IsParking){if(a.CarparkId!=b.CarparkId)return false;}
            else if(a.Tile!=b.Tile)return false;
            if(Rules.Version==GameVersion.OriginalReference&&!a.IsParking&&!b.IsParking&&a.Incoming<8&&b.Incoming<8)return ConnectionsIntersect(a,b,false);
            string key=string.CompareOrdinal(a.Key,b.Key)<0?a.Key+"/"+b.Key:b.Key+"/"+a.Key;
            if(conflictCache.TryGetValue(key,out bool value))return value;
            bool conflict=false;
            for(int i=1;i<a.Samples.Length-1&&!conflict;i++)for(int j=1;j<b.Samples.Length-1;j++)
                if(Point.Distance(a.Samples[i],b.Samples[j])<.13){conflict=true;break;}
            conflictCache[key]=conflict;return conflict;
        }

        sealed class MotionSnapshot
        {
            public Vehicle Car;public Lane Lane;public int Index;public double Distance,Speed,Acceleration;public Point Position;
        }

        bool MayEnter(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out string why,out int blocker)
        {
            why="";blocker=-1;
            if(!lane.IsMotorway&&IsRailCrossingClosed(lane.Tile)){why="Train crossing";return false;}
            // A red light refuses first, so a red-blocked car never takes the carpark gate.
            if(Rules.Version==GameVersion.OriginalReference&&CarparkApproachGate&&!lane.IsParking&&!lane.IsMotorway&&Signals.ContainsKey(lane.Tile)&&!LightAllowsEntry(lane))
            {why="Traffic light";return false;}
            // A gate refusal names its owner so blocking-cycle recovery can see it; a shoving car may pass.
            if(Rules.Version==GameVersion.OriginalReference&&CarparkApproachGate&&!(car.Shoving&&car.ShovingLane==lane.Key&&IsImmediateNext(car,lane))&&!CarparkThroatAllows(car,lane))
            {why="Carpark entrance merge";blocker=CarparkGateOwner(car,lane);return false;}
            var parcel=AccessBuildingAt(lane.Tile);
            if(Rules.Version==GameVersion.Custom&&parcel!=null&&!parcel.IsHouse&&car.Stage==TripStage.Outbound&&
                Cars.Any(v=>v.Id!=car.Id&&SameCarpark(v.ShopId,parcel.Id)&&(v.Stage==TripStage.EnteringParking||v.Stage==TripStage.LeavingParking)))
            {why="Carpark access occupied";return false;}
            // Internal lot paths can revisit the same parcel many times. Tile-level
            // approach ordering would make an entering car yield to the car behind it.
            // Physical local clearance below governs these short circulation segments.
            if(lane.IsParking&&Rules.Version==GameVersion.OriginalReference)return MayEnterParkingOriginal(car,lane,snapshot,out why,out blocker);
            if(Rules.Version==GameVersion.OriginalReference)return MayEnterOriginal(car,lane,snapshot,out why,out blocker);
            if(!lane.IsJunction&&!lane.IsRoundabout&&!lane.IsParking)return true;
            if(!SignalAllows(lane.Tile,lane.Incoming)){why="Traffic light";return false;}
            foreach(var other in snapshot)
            {
                if(other.Car.Id==car.Id)continue;
                // Release the crossing once a traversing car reaches its exit section.
                // Retaining its entire previous lane also locks adjacent junctions together.
                if(other.Distance<=other.Lane.Length-Rules.CarLength&&Conflicts(lane,other.Lane))
                {why=lane.IsRoundabout?"Yield to circulating traffic":"Crossing vehicle";return false;}
            }
            // Original comparator prioritizes circulating vehicles, distance, then registration time.
            if(TryApproach(car,lane.Tile,out _,out double ownDistance))
                foreach(var other in snapshot)
                {
                    if(other.Car.Id==car.Id||!TryApproach(other.Car,lane.Tile,out var target,out double theirDistance))continue;
                    if(!Conflicts(lane,target)||!SignalAllows(lane.Tile,target.Incoming))continue;
                    // A car that cannot enter because a conflicting vehicle still occupies its
                    // target does not hold priority. Otherwise it can wait on a car that is itself
                    // waiting for this one, through an adjacent junction or roundabout.
                    if(ConflictOccupied(target,other.Car,snapshot))continue;
                    bool ownRing=OnTargetRoundabout(car,lane),theirRing=OnTargetRoundabout(other.Car,lane);
                    double ownRegistered=car.ApproachRegistered.TryGetValue(lane.Key,out var ownTime)?ownTime:Time;
                    double theirRegistered=other.Car.ApproachRegistered.TryGetValue(target.Key,out var theirTime)?theirTime:Time;
                    bool priority=theirRing&&!ownRing||theirRing==ownRing&&
                        (theirDistance<ownDistance-1e-6||Math.Abs(theirDistance-ownDistance)<1e-6&&theirRegistered<ownRegistered||
                        Math.Abs(theirDistance-ownDistance)<1e-6&&theirRegistered==ownRegistered&&other.Car.Id<car.Id);
                    if(priority){why=lane.IsRoundabout?"Roundabout entry yield":"Approaching vehicle priority";return false;}
                }
            return true;
        }

        bool ConflictOccupied(Lane target,Vehicle entering,List<MotionSnapshot> snapshot)
        {
            foreach(var other in snapshot)
                if(other.Car.Id!=entering.Id&&other.Speed<.02&&other.Distance<=other.Lane.Length-Rules.CarLength&&Conflicts(target,other.Lane))return true;
            return false;
        }

        bool OnTargetRoundabout(Vehicle car,Lane target)
        {
            var round=RoundaboutAt(target.Tile);
            return round!=null&&car.CurrentLane!=null&&car.CurrentLane.IsRoundabout&&round.Ring.Contains(car.CurrentLane.Tile);
        }

        void RegisterApproaches(Vehicle car)
        {
            var active=new HashSet<string>();double distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count&&distance<=Rules.LookaheadDistance;i++)
            {
                var lane=car.Lanes[i];
                if(lane.IsJunction||lane.IsRoundabout||lane.IsParking)
                {active.Add(lane.Key);if(!car.ApproachRegistered.ContainsKey(lane.Key))car.ApproachRegistered[lane.Key]=Time;}
                distance+=lane.Length;
            }
            foreach(var key in car.ApproachRegistered.Keys.Where(k=>!active.Contains(k)).ToArray())car.ApproachRegistered.Remove(key);
        }

        internal double DesiredMovementSpeed(Vehicle car)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return car.CurrentLane.SpeedLimit;
            double length=0,weighted=0,minimum=double.PositiveInfinity;
            for(int i=car.RouteIndex;i<car.Lanes.Count&&length<Rules.LookaheadDistance;i++)
            {
                var lane=car.Lanes[i];double available=lane.Length-(i==car.RouteIndex?car.DistanceAlongLane:0);
                double take=Math.Min(available,Rules.LookaheadDistance-length);
                minimum=Math.Min(minimum,lane.SpeedLimit);weighted+=lane.SpeedLimit*take;length+=take;
            }
            // Reference ordinary movement uses a distance-weighted lane average;
            // motorway movement instead uses the minimum in the same lookahead.
            double laneValue=car.CurrentLane.IsMotorway?minimum:length>1e-9?weighted/length:car.CurrentLane.SpeedLimit;
            return laneValue*Rules.MovementSpeedMultiplier;
        }

        void UpdateVehicles()
        {
            ReleaseCarparkThroats();
            foreach(var car in Cars)
            {
                RefreshJourney(car);
                if(car.Stage==TripStage.Parking)
                {
                    car.Dwell-=Rules.TickSeconds;
                    var shop=Buildings[car.ShopId];
                    // Original eviction: a full lot sends its longest-parked car home only while a car is on its way
                    // (waiting demand, i.e. dispatched pins) to one of its destinations.
                    bool full=shop.Parking.All(p=>p>=0)&&Buildings.Any(b=>!b.IsHouse&&b.CarparkId==shop.CarparkId&&b.Reserved>0);
                    bool longest=Cars.Where(v=>SameCarpark(v.ShopId,shop.Id)&&v.Stage==TripStage.Parking).OrderBy(v=>v.Dwell).FirstOrDefault()==car;
                    bool accessBusy=Cars.Any(v=>v.Id!=car.Id&&SameCarpark(v.ShopId,shop.Id)&&
                        (v.Stage==TripStage.EnteringParking||v.Stage==TripStage.LeavingParking||
                        v.Stage==TripStage.Outbound&&v.CurrentLane!=null&&HasAccess(shop,v.CurrentLane.Tile)));
                    bool finished=Rules.Version==GameVersion.OriginalReference?car.Dwell<0:car.Dwell<=0;
                    if((finished||full&&longest)&&(Rules.Version==GameVersion.OriginalReference||!accessBusy))StartLeavingParking(car);
                }
                else if(car.Stage==TripStage.Returning&&!car.Moving)FinishHome(car);
                else if(car.Stage==TripStage.EnteringParking&&car.HasDelivered&&!car.DrivingThrough)car.Dwell-=Rules.TickSeconds;
            }
            var snapshot=Cars.Where(c=>c.Moving).Select(c=>new MotionSnapshot{Car=c,Lane=c.CurrentLane,Index=c.RouteIndex,
                Distance=c.DistanceAlongLane,Speed=c.Speed,Acceleration=c.Acceleration,Position=c.Position}).ToList();
            if(Rules.Version!=GameVersion.OriginalReference)foreach(var state in snapshot)RegisterApproaches(state.Car);
            var obstacles=new Dictionary<int,ObstacleRecord>();var nextSpeeds=new Dictionary<int,double>();
            var proposals=new List<(Vehicle car,double speed,double acceleration,double distance,string obstacle)>();
            foreach(var state in snapshot)
            {
                var car=state.Car;double desired=DesiredMovementSpeed(car),gap=1e6,leaderSpeed=desired,leaderAcceleration=0;
                string obstacle="";double stop=double.PositiveInfinity;int leaderId=-1,blocker=-1;double blockingDistance=double.PositiveInfinity;string blockedLane="";var blockedTile=new Cell(-1,-1);
                // Follow the next vehicle on this directed lane or a shared outgoing lane.
                foreach(var other in snapshot)
                {
                    if(other.Car.Id==car.Id)continue;
                    double distance=double.PositiveInfinity;
                    if(other.Lane.Key==state.Lane.Key)
                    {
                        double difference=other.Distance-state.Distance;
                        if(difference>1e-8||Math.Abs(difference)<1e-8&&other.Car.Id<car.Id)distance=Math.Max(0,difference);
                    }
                    else
                    {
                        double ahead=state.Lane.Length-state.Distance;
                        for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++)
                        {
                            if(car.Lanes[i].Key==other.Lane.Key){distance=ahead+other.Distance;break;}
                            ahead+=car.Lanes[i].Length;if(ahead>Rules.LookaheadDistance)break;
                        }
                    }
                    if(distance<gap){gap=distance;leaderSpeed=other.Speed;leaderAcceleration=other.Acceleration;obstacle="Queue ahead";leaderId=other.Car.Id;}
                }
                // A zero-length parcel lane is omitted by MakeLanes, so a car
                // may already be on its final surface lane. Gate that approach
                // here as well as future-lane transitions.
                if(Rules.Version==GameVersion.OriginalReference&&CarparkApproachGate&&!state.Lane.IsParking&&TryCarparkGate(car,state.Lane,out _,out _,out _)&&
                    !(car.Shoving&&car.ShovingLane==state.Lane.Key)&&!CarparkThroatAllows(car,state.Lane))
                {
                    stop=0;blockingDistance=0;blocker=CarparkGateOwner(car,state.Lane);blockedLane=state.Lane.Key;
                    if(TryCarparkGate(car,state.Lane,out _,out var gateAccess,out _))blockedTile=gateAccess;
                    obstacle="Carpark entrance merge";
                }
                double aheadDistance=state.Lane.Length-state.Distance;double? slowGap=null;bool blockedControlled=false;double blockedAhead=double.PositiveInfinity;
                for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++)
                {
                    var next=car.Lanes[i];
                    if(aheadDistance<Rules.LookaheadDistance)
                    {
                        if(Rules.Version!=GameVersion.OriginalReference)
                            desired=Math.Min(desired,Math.Sqrt(next.SpeedLimit*next.SpeedLimit+2*Rules.MaxDeceleration*Math.Max(0,aheadDistance-.1)));
                        if(!MayEnter(car,next,snapshot,out string reason,out int entryBlocker))
                        {if(aheadDistance<blockingDistance){blockingDistance=aheadDistance;blocker=entryBlocker;blockedLane=next.Key;blockedTile=next.Tile;}
                            bool entrance=next.IsParking&&next.Key.Contains(":entrance:")||
                            car.Stage==TripStage.Outbound&&i==car.Lanes.Count-1&&!next.IsParking;
                            stop=Math.Min(stop,Math.Max(0,aheadDistance-(Rules.Version==GameVersion.OriginalReference?Rules.FollowingGap*.5:entrance?Rules.CarLength+.05:Rules.CarLength*.35)));obstacle=reason;
                            if(Rules.Version==GameVersion.OriginalReference){blockedControlled=IsControlledLane(next)||next.IsRoundabout;blockedAhead=aheadDistance;}break;}
                        // Original intersection slowdown: with nothing ahead yet, cap acceleration as if a car moving at
                        // 0.55 of the desired speed sat at the entry of an uncontrolled junction with 3+ real roads.
                        if(Rules.Version==GameVersion.OriginalReference&&slowGap==null&&gap>aheadDistance&&aheadDistance>2*Rules.CarLength&&
                            !next.IsParking&&!next.IsMotorway&&!IsControlledLane(next)&&RoadsForIntersectionSlowdown(next.Tile)>=3)
                            slowGap=aheadDistance+Rules.CarLength-Rules.FollowingGap*.5;
                    }
                    aheadDistance+=next.Length;if(aheadDistance>Rules.LookaheadDistance)break;
                }
                double remaining=state.Lane.Length-state.Distance;
                for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)remaining+=car.Lanes[i].Length;
                desired=Math.Min(desired,Math.Sqrt(2*Rules.MaxDeceleration*Math.Max(0,remaining)));
                double maximumAcceleration=Rules.Version==GameVersion.OriginalReference?OriginalMaximumAcceleration(car,state.Lane,state.Distance):
                    state.Lane.IsRoundabout?Rules.RoundaboutAcceleration:state.Lane.IsJunction?Rules.ControlledAcceleration:Rules.MaxAcceleration;
                double acceleration=AccelerationFor(gap,state.Speed,leaderSpeed,leaderAcceleration,Math.Max(.001,desired),maximumAcceleration);
                if(!double.IsInfinity(stop))
                {
                    double held=AccelerationFor(stop+Rules.CarLength,state.Speed,0,0,desired,Rules.Version==GameVersion.OriginalReference?maximumAcceleration:Rules.ControlledAcceleration);
                    // Original: blocked at a signal-controlled chunk within two vehicle lengths doubles the acceleration.
                    if(Rules.Version==GameVersion.OriginalReference&&blockedControlled&&blockedAhead<2*Rules.CarLength&&held<=acceleration)held*=2;
                    acceleration=Math.Min(acceleration,held);
                }
                else if(slowGap!=null)
                {
                    double target=.55*Math.Max(.001,desired);
                    acceleration=Math.Min(acceleration,AccelerationFor(slowGap.Value,state.Speed,target,0,target,maximumAcceleration,1.6));
                }
                double speed=Math.Max(0,state.Speed+acceleration*Rules.TickSeconds);
                double travel=(state.Speed+speed)*.5*Rules.TickSeconds;
                // Hard clearance bounds are independent of acceleration integration and tick ordering.
                travel=Math.Min(travel,Math.Max(0,gap-Rules.CarLength-Rules.FollowingGap));
                travel=Math.Min(travel,stop);
                if(travel<=1e-7){speed=0;if(obstacle.Length==0)obstacle="Driveway queue";}
                proposals.Add((car,speed,acceleration,Math.Max(0,travel),obstacle));
                if(Rules.Version==GameVersion.OriginalReference)
                {var record=NearestObstacle(leaderId,gap,blockingDistance,blocker,blockedLane,remaining,Rules.LookaheadDistance);record.BlockedTile=blockedTile;obstacles[car.Id]=record;nextSpeeds[car.Id]=speed;}
            }
            if(Rules.Version==GameVersion.OriginalReference)
            {
                foreach(var car in Cars){car.ObstacleState=ObstacleKind.None;car.ObstacleCar=-1;car.ObstacleDistance=0;}
                foreach(var item in obstacles){var car=CarById(item.Key);car.ObstacleState=item.Value.Kind;car.ObstacleCar=item.Value.Car;car.ObstacleDistance=item.Value.Distance;car.BlockingTile=item.Value.BlockedTile;}
                MarkBlockingCycles(obstacles,nextSpeeds);
            }
            foreach(var proposal in proposals)
            {
                var car=proposal.car;double travel=proposal.distance;
                car.Speed=travel<proposal.distance-1e-8?0:proposal.speed;car.Acceleration=proposal.acceleration;
                car.Obstacle=travel<proposal.distance-1e-8?"Carpark lane clearance":proposal.obstacle;car.WaitingAtSignal=car.Obstacle=="Traffic light";
                car.WaitingAtIntersection=car.Obstacle.Contains("priority")||car.Obstacle.Contains("Crossing")||car.Obstacle.Contains("yield");
                if(car.Speed<.02&&car.Stage!=TripStage.Parking){car.Waiting+=Rules.TickSeconds;car.TotalWaiting+=Rules.TickSeconds;}else car.Waiting=0;
                AdvanceVehicle(car,travel);
            }
        }

        public bool VehicleBodiesOverlap(Point a,Point forwardA,Point b,Point forwardB)
        {
            var sideA=forwardA.Right;var sideB=forwardB.Right;var delta=b-a;
            foreach(var axis in new[]{forwardA,sideA,forwardB,sideB})
            {
                double extentA=Math.Abs(Point.Dot(axis,forwardA))*Rules.CarLength*.5+Math.Abs(Point.Dot(axis,sideA))*.085;
                double extentB=Math.Abs(Point.Dot(axis,forwardB))*Rules.CarLength*.5+Math.Abs(Point.Dot(axis,sideB))*.085;
                if(Math.Abs(Point.Dot(delta,axis))>=extentA+extentB-.00001)return false;
            }
            return true;
        }

        public double AccelerationFor(double centerGap,double speed,double leadingSpeed,double leadingAcceleration,double desired,double maximumAcceleration,double decelerationExponent=6)
        {
            // Independently expressed car-following equations matching the recovered reference model.
            if(desired<1e-6)return -Rules.MaxDeceleration;
            double space=Math.Max(centerGap-Rules.CarLength,Rules.FollowingGap),relative=speed-leadingSpeed;
            double free=speed<=desired?maximumAcceleration*(1-Math.Pow(speed/desired,4)):
                -Rules.MaxDeceleration*(1-Math.Pow(desired/Math.Max(.001,speed),maximumAcceleration*decelerationExponent/Rules.MaxDeceleration));
            double wanted=Rules.FollowingGap+Math.Max(0,speed*Rules.DesiredTimeGap+speed*relative/(2*Math.Sqrt(maximumAcceleration*Rules.MaxDeceleration)));
            double ratio=wanted/space,interaction=maximumAcceleration*(1-ratio*ratio);
            double combined=speed<=desired?(ratio>=1?interaction:free*(1-Math.Pow(ratio,2*maximumAcceleration/Math.Max(.001,free)))):
                ratio>=1?free+interaction:free;
            double anticipatory;
            double term=2*space*leadingAcceleration;
            if(leadingSpeed*relative<-term&&Math.Abs(leadingSpeed*leadingSpeed-term)>1e-6)
                anticipatory=speed*speed*leadingAcceleration/(leadingSpeed*leadingSpeed-term);
            else anticipatory=leadingAcceleration-(relative>=0?relative*relative/(2*space):0);
            anticipatory=Math.Min(anticipatory,maximumAcceleration);
            double result=combined>=anticipatory?combined:.8*combined+.2*(anticipatory+Rules.MaxDeceleration*Math.Tanh((combined-anticipatory)/Rules.MaxDeceleration));
            return Math.Max(-Rules.MaxDeceleration,Math.Min(maximumAcceleration,double.IsNaN(result)?-Rules.MaxDeceleration:result));
        }

        void AdvanceVehicle(Vehicle car,double distance)
        {
            if(distance>0)car.LastMoved=Time;
            while(car.Moving)
            {
                double remaining=car.CurrentLane.Length-car.DistanceAlongLane;
                if(distance<remaining-1e-8){car.DistanceAlongLane+=distance;break;}
                distance-=remaining;if(car.CurrentLane.ReleasesParking)ReleaseParkingSlot(car);
                if(car.CurrentLane.DeliversDriveThrough&&car.DrivingThrough)Deliver(car);
                car.RouteIndex++;car.DistanceAlongLane=0;car.SegmentEntered=Time;car.Shoving=false;car.ShovingLane="";
                if(car.RouteIndex>=car.Lanes.Count){FinishJourney(car);break;}
                if(Rules.Version==GameVersion.OriginalReference){car.ApproachRegistered.Remove(car.CurrentLane.Key);car.CommittedAt.Remove(car.CurrentLane.Key);NoteCommitments(car);}
                RefreshJourney(car);UpdateLegs(car);
            }
            if(car.Moving)
            {car.At=car.CurrentLane.Tile;car.Next=car.CurrentLane.Next;car.Progress=car.DistanceAlongLane/car.CurrentLane.Length;}
        }

        void FinishJourney(Vehicle car)
        {
            car.Speed=0;car.DistanceAlongLane=0;
            switch(car.Stage)
            {
                case TripStage.Outbound:StartParking(car);break;
                case TripStage.EnteringParking:
                    bool arrived=car.HasDelivered&&Rules.Version==GameVersion.OriginalReference;Deliver(car);
                    if(car.DrivingThrough){car.Stage=TripStage.Returning;SetJourney(car,car.ReturnRoute);break;}
                    // Parked cars receive no movement updates; do not keep the approach wait.
                    car.Stage=TripStage.Parking;car.Waiting=0;car.ParkedPosition=ParkingPoint(Buildings[car.ShopId],car.ParkingSlot);
                    car.ParkedHeading=Rules.Version==GameVersion.OriginalReference?ParkingHeading(Buildings[car.ShopId],car.DestinationAccess):new Point(0,-1);
                    if(!arrived)car.Dwell=Rules.ServiceSeconds;break;
                case TripStage.LeavingParking:
                    ReleaseParkingSlot(car);car.Stage=TripStage.Returning;SetJourney(car,car.ReturnRoute);break;
                case TripStage.Returning:FinishHome(car);break;
            }
        }
        public Point ParkingPoint(Building shop,int slot)
        {
            if(Rules.Version==GameVersion.OriginalReference)return ParkingBay(shop,slot).Center;
            return new Point(shop.Cell.X+.18+(slot+.5)*1.64/shop.Parking.Length,shop.Cell.Y+2.25);
        }
        Point ParkingVector(Building shop,double along,double across)=>LayoutPoint(shop,along,across)-LayoutPoint(shop,0,0);

        void StartParking(Vehicle car)
        {
            var shop=Buildings[car.ShopId];car.At=car.DestinationAccess;car.Next=car.DestinationAccess;
            var available=Enumerable.Range(0,shop.Parking.Length).Where(i=>shop.Parking[i]<0).ToList();
            if(available.Count==0)
            {
                car.DrivingThrough=true;
                if(Rules.Version==GameVersion.OriginalReference)
                {car.Stage=TripStage.EnteringParking;car.Lanes=ParkingDriveThrough(shop,car.DestinationAccess);car.RouteIndex=0;car.DistanceAlongLane=0;RegisterRoute(car,false);return;}
                Deliver(car);car.Stage=TripStage.Returning;SetJourney(car,car.ReturnRoute);return;
            }
            int slot=available.Count==1?available[0]:available[random.Next(available.Count)];
            car.ParkingSlot=slot;shop.Parking[slot]=car.Id;car.Stage=TripStage.EnteringParking;
            if(Rules.Version==GameVersion.OriginalReference)
            {car.Lanes=ParkingRoute(shop,car.DestinationAccess,slot);car.RouteIndex=0;car.DistanceAlongLane=0;RegisterRoute(car,false);return;}
            Point a=new Point(car.DestinationAccess),b=ParkingPoint(shop,slot);
            var lane=CreateLane(Cubic(a,a+ParkingVector(shop,.25,.15),b+ParkingVector(shop,0,.35),b,16),car.DestinationAccess,car.DestinationAccess,car.DestinationAccess,0,0);
            lane.IsParking=true;lane.SpeedLimit=Rules.CarSpeed*.6;lane.Key=$"parking-in:{shop.CarparkId}:{slot}";
            car.Lanes=new List<Lane>{lane};car.RouteIndex=0;car.DistanceAlongLane=0;
        }
        void StartLeavingParking(Vehicle car)
        {
            if(Rules.Version==GameVersion.OriginalReference)
            {
                var destination=Buildings[car.ShopId];List<Cell> best=null;double cost=double.PositiveInfinity;
                foreach(var access in Accesses(destination))
                {
                    var route=FindRoute(access,Buildings[car.HomeId].Access);if(route.Count<2)continue;
                    double value=RouteCost(route);if(value<cost){cost=value;best=route;}
                }
                if(best!=null){car.DestinationAccess=best[0];car.ReturnRoute=best;}
                car.Lanes=ParkingRoute(destination,car.DestinationAccess,car.ParkingSlot,true);car.Stage=TripStage.LeavingParking;car.RouteIndex=0;car.DistanceAlongLane=0;car.Speed=0;
                car.LegMarks.Clear();car.ParkingLegAt=-1;car.ParkingLegAttached=false;AppendReturnLanes(car);RegisterRoute(car,false);return;
            }
            var shop=Buildings[car.ShopId];Point a=ParkingPoint(shop,car.ParkingSlot),b=new Point(car.DestinationAccess);
            var lane=CreateLane(Cubic(a,a+ParkingVector(shop,0,.4),b+ParkingVector(shop,.4,.35),b,16),car.DestinationAccess,car.DestinationAccess,car.DestinationAccess,0,0);
            lane.IsParking=true;lane.SpeedLimit=Rules.CarSpeed*.6;lane.Key=$"parking-out:{shop.CarparkId}:{car.ParkingSlot}";
            car.Stage=TripStage.LeavingParking;car.Lanes=new List<Lane>{lane};car.RouteIndex=0;car.DistanceAlongLane=0;car.Speed=0;
        }
        void ReleaseParkingSlot(Vehicle car)
        {if(car.ParkingSlot>=0&&car.ShopId>=0)Buildings[car.ShopId].Parking[car.ParkingSlot]=-1;car.ParkingSlot=-1;}
        void FinishHome(Vehicle car)
        {
            car.Stage=TripStage.Home;car.Waiting=0;car.At=Buildings[car.HomeId].Cell;car.Next=car.At;car.Lanes.Clear();car.Route.Clear();
            car.ReturnRoute.Clear();car.ApproachRegistered.Clear();car.LegMarks.Clear();car.ParkingLegAt=-1;car.ParkingLegAttached=false;car.ShopId=-1;car.Speed=0;car.ArrivedHome=Time;car.RouteIndex=0;car.DistanceAlongLane=0;car.Obstacle="";
        }
    }
}
