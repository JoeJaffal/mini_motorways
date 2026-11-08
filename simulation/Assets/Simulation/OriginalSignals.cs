using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    // OriginalReference traffic-light phases and permissions, independently implemented from the rule description in
    // docs/training/simulator-repairs-2026-11-08/ORIGINAL_SIGNALS_CARPARKS_ANSWER.md (installed constants; no original
    // code). Custom keeps UpdateSignals/BestSignalPair/SignalAllows in TrafficControl.cs.
    // Not reproduced: the "lane replacement" (hot-swap) obstacle, which has no equivalent here; the original direction
    // enumeration order for pairing and same-weight ties (our order is kept); inbound-list order is approximated by
    // registration time, then vehicle id.
    public sealed partial class TrafficWorld
    {
        const double MothballedAgeMultiplier=4,NonCrossingAgeModifier=.10000000149011612,CarparkInputAgeMultiplier=10,BlockedCarWeightModifier=.10000000149011612;

        struct SignalCandidate{public Vehicle Car;public Lane Lane;public double Distance;public int Approach;}

        static int ApproachOf(Lane lane)=>(lane.Incoming+4)%8;

        // Amber leaves ActivePair unchanged and permission is tested on the active pair only.
        bool LightPermits(Lane lane)=>!Signals.TryGetValue(lane.Tile,out var s)||(s.ActivePair&(1<<ApproachOf(lane)))!=0;

        // American red-light rules: the first outbound direction found in three successive turns from the approach
        // toward the right is the non-crossing exit; no such direction means every connection crosses.
        bool IsNonCrossing(Lane lane)
        {
            int approach=ApproachOf(lane),mask=Connections[lane.Tile.X,lane.Tile.Y];
            for(int k=1;k<=3;k++){int d=(approach-k+8)%8;if((mask&(1<<d))!=0)return lane.Outgoing==d;}
            return false;
        }

        bool LightAllowsEntry(Lane lane)=>LightPermits(lane)||IsNonCrossing(lane);

        bool BlockedInChunk(Vehicle car,Cell chunk)=>car.ObstacleState==ObstacleKind.BlockingJunction&&car.BlockingTile==chunk;

        // Committed inbound candidates of a signalled chunk: the chosen lane is among the first two remaining planned
        // lanes; distance is along the route to that lane's start. Ordered as the chunk's inbound list.
        List<SignalCandidate> SignalCandidates(Cell chunk)
        {
            var list=new List<(SignalCandidate c,double registered)>();
            foreach(var car in Cars)
            {
                if(!car.Moving)continue;double distance=car.CurrentLane.Length-car.DistanceAlongLane;
                for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+3);i++)
                {
                    var lane=car.Lanes[i];
                    if(lane.Tile==chunk&&!lane.IsMotorway&&!lane.IsParking)
                    {
                        double registered=car.ApproachRegistered.TryGetValue(lane.Key,out var r)?r:Time;
                        list.Add((new SignalCandidate{Car=car,Lane=lane,Distance=distance,Approach=ApproachOf(lane)},registered));break;
                    }
                    distance+=lane.Length;
                }
            }
            return list.OrderBy(x=>x.registered).ThenBy(x=>x.c.Car.Id).Select(x=>x.c).ToList();
        }

        // Rotation guard count: the scan ends at the first committed candidate blocked inside this chunk, before its
        // direction is matched; there is no speed filter.
        int NearbyCount(SignalState signal,List<SignalCandidate> candidates)
        {
            int count=0;
            foreach(var c in candidates)
            {
                if(BlockedInChunk(c.Car,signal.Cell))break;
                if((signal.ActivePair&(1<<c.Approach))==0)continue;
                if(c.Distance<Rules.SignalNearbyDistance)count++;
            }
            return count;
        }

        double PairWeight(SignalState signal,int pair,List<SignalCandidate> candidates)
        {
            double sum=0;
            for(int d=0;d<8;d++)
            {
                if((pair&(1<<d))==0)continue;bool discount=true;
                foreach(var c in candidates.Where(x=>x.Approach==d))
                {
                    double committed=c.Car.CommittedAt.TryGetValue(c.Lane.Key,out var at)?at:Time;
                    double age=Math.Min(1,Math.Max(0,(Time-committed)/Rules.SignalMaxWaitingWeightSeconds));age*=age;
                    if(PendingRemoval[c.Lane.Tile.X,c.Lane.Tile.Y])age*=MothballedAgeMultiplier;
                    if(IsNonCrossing(c.Lane)){if(discount)age*=NonCrossingAgeModifier;}else discount=false;
                    if(c.Car.CurrentLane.IsParking)age*=CarparkInputAgeMultiplier;
                    double contribution=age+1;
                    if(pair==signal.ActivePair&&BlockedInChunk(c.Car,signal.Cell))contribution*=BlockedCarWeightModifier;
                    sum+=contribution;
                }
            }
            return sum;
        }

        // Strict-greater winner in stored pair order; all-zero demand keeps the current pair.
        int WinningPair(SignalState signal,List<SignalCandidate> candidates,bool excludeCurrent)
        {
            int best=-1;double weight=0;
            foreach(int pair in signal.Pairs)
            {
                if(excludeCurrent&&pair==signal.ActivePair)continue;
                double w=PairWeight(signal,pair,candidates);if(w>weight){best=pair;weight=w;}
            }
            if(best>=0)return best;
            if(!excludeCurrent)return signal.ActivePair;
            int index=signal.Pairs.IndexOf(signal.ActivePair);return signal.Pairs[(index+1)%signal.Pairs.Count];
        }

        void UpdateSignalsOriginal()
        {
            foreach(var signal in Signals.Values)
            {
                signal.Elapsed+=Rules.TickSeconds;
                if(signal.Pairs.Count==0)UpdateSignalPairs(signal);
                if(signal.Pairs.Count==0)continue;
                if(signal.Amber)
                {
                    if(signal.Elapsed>Rules.SignalAmberSeconds)
                    {signal.ActivePair=WinningPair(signal,SignalCandidates(signal.Cell),true);signal.Amber=false;signal.Elapsed=0;}
                    continue;
                }
                if(!(signal.Elapsed>Rules.SignalGreenSeconds||signal.Overtime&&signal.Elapsed>Rules.SignalOvertimeSeconds))continue;
                var candidates=SignalCandidates(signal.Cell);int nearby=NearbyCount(signal,candidates);
                bool rotate=!(nearby>0&&nearby<Rules.SignalMinimumNearbyCars)&&signal.Pairs.Count>1&&WinningPair(signal,candidates,false)!=signal.ActivePair;
                if(rotate){signal.Amber=true;signal.Overtime=false;}else signal.Overtime=true;
                signal.Elapsed=0;
            }
        }

        // A planned lane is committed once it is among the first two remaining lanes; remember when that first happened.
        void NoteCommitments(Vehicle car)
        {
            if(Rules.Version!=GameVersion.OriginalReference||!car.Moving)return;
            for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+3);i++)
                if(!car.CommittedAt.ContainsKey(car.Lanes[i].Key))car.CommittedAt[car.Lanes[i].Key]=Time;
        }
    }
}
