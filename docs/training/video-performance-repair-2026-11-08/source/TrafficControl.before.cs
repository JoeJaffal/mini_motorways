using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly Dictionary<(int,Cell),int> carparkThroats=new Dictionary<(int,Cell),int>();
        bool CarparkThroatAllows(Vehicle car,Lane lane)
        {
            if(car.ShopId<0)return true;
            bool entrance=car.Stage==TripStage.Outbound&&HasAccess(Buildings[car.ShopId],lane.Tile);
            bool exit=lane.IsParking&&lane.Key.Contains(":exit:");if(!entrance&&!exit)return true;
            double distance=car.CurrentLane.Length-car.DistanceAlongLane;
            for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)
            {if(ReferenceEquals(car.Lanes[i],lane))break;distance+=car.Lanes[i].Length;}
            if(distance>Rules.CarLength+.3)return true;
            var key=(Buildings[car.ShopId].CarparkId,car.DestinationAccess);
            if(carparkThroats.TryGetValue(key,out int owner))return owner==car.Id;
            // A follower must never reserve the exit in front of its leader.
            Vehicle nearest=car;double nearestDistance=distance;
            foreach(var other in Cars.Where(v=>v.Id!=car.Id&&v.Moving&&SameCarpark(v.ShopId,car.ShopId)&&v.DestinationAccess==car.DestinationAccess&&
                (v.Stage==TripStage.Outbound||v.Stage==TripStage.LeavingParking)))
            {
                double otherDistance=other.RouteIndex==other.Lanes.Count-1?-other.DistanceAlongLane:other.CurrentLane.Length-other.DistanceAlongLane;
                for(int i=other.RouteIndex+1;i<other.Lanes.Count-1;i++)otherDistance+=other.Lanes[i].Length;
                if(otherDistance<nearestDistance-1e-8||Math.Abs(otherDistance-nearestDistance)<1e-8&&other.Id<nearest.Id)
                {nearest=other;nearestDistance=otherDistance;}
            }
            carparkThroats[key]=nearest.Id;return nearest.Id==car.Id;
        }
        void ReleaseCarparkThroats()
        {
            foreach(var item in carparkThroats.ToArray())
            {
                var car=Cars.Find(c=>c.Id==item.Value);
                bool keep=car!=null&&car.ShopId>=0&&car.Moving&&
                    (car.Stage==TripStage.Outbound||car.Stage==TripStage.LeavingParking||
                     car.Stage==TripStage.EnteringParking&&car.CurrentLane.Key.Contains(":entrance:")||
                     car.Stage==TripStage.Returning&&Point.Distance(car.Position,ParkingAccessPoint(Buildings[car.ShopId],item.Key.Item2,false))<Rules.CarLength+.1);
                if(!keep)carparkThroats.Remove(item.Key);
            }
        }
        void UpdateSignalPairs(SignalState signal)
        {
            int remaining=Connections[signal.Cell.X,signal.Cell.Y];var masks=new List<int>();
            for(int d=0;d<4;d++)if((remaining&(1<<d))!=0&&(remaining&(1<<(d+4)))!=0)
            {int mask=(1<<d)|(1<<(d+4));masks.Add(mask);remaining&=~mask;}
            for(int d=0;d<8;d++)
            {
                if((remaining&(1<<d))==0)continue;
                int a=(d+3)%8,b=(d+5)%8;
                if((remaining&(1<<a))!=0&&(remaining&(1<<b))!=0)continue;
                int pair=(remaining&(1<<a))!=0?a:(remaining&(1<<b))!=0?b:-1;
                if(pair>=0){int mask=(1<<d)|(1<<pair);masks.Add(mask);remaining&=~mask;}
            }
            for(int d=0;d<8;d++)if((remaining&(1<<d))!=0)masks.Add(1<<d);
            signal.Pairs=masks;
            if(!masks.Contains(signal.ActivePair))signal.ActivePair=masks.Count==0?0:masks[0];
        }

        public int SignalPhase(Cell c)=>Signals.TryGetValue(c,out var s)?s.Amber?-1:(s.ActivePair&17)!=0?0:1:-1;
        public bool SignalAllows(Cell cell,int incoming)
        {
            if(!Signals.TryGetValue(cell,out var s))return true;
            int approach=(incoming+4)%8;return !s.Amber&&(s.ActivePair&(1<<approach))!=0;
        }

        void UpdateSignals()
        {
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
        bool Conflicts(Lane a,Lane b)
        {
            if(a.IsMotorway||b.IsMotorway)return false;
            if(a.Key==b.Key)return false;
            if(a.IsParking&&b.IsParking){if(a.CarparkId!=b.CarparkId)return false;}
            else if(a.Tile!=b.Tile)return false;
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

        bool MayEnter(Vehicle car,Lane lane,List<MotionSnapshot> snapshot,out string why)
        {
            why="";
            if(!lane.IsMotorway&&IsRailCrossingClosed(lane.Tile)){why="Train crossing";return false;}
            if(Rules.Version==GameVersion.OriginalReference&&!CarparkThroatAllows(car,lane))
            {why="Carpark entrance merge";return false;}
            var parcel=AccessBuildingAt(lane.Tile);
            if(Rules.Version==GameVersion.Custom&&parcel!=null&&!parcel.IsHouse&&car.Stage==TripStage.Outbound&&
                Cars.Any(v=>v.Id!=car.Id&&SameCarpark(v.ShopId,parcel.Id)&&(v.Stage==TripStage.EnteringParking||v.Stage==TripStage.LeavingParking)))
            {why="Carpark access occupied";return false;}
            // Internal lot paths can revisit the same parcel many times. Tile-level
            // approach ordering would make an entering car yield to the car behind it.
            // Physical local clearance below governs these short circulation segments.
            if(lane.IsParking&&Rules.Version==GameVersion.OriginalReference)return true;
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
                    bool full=shop.Parking.All(p=>p>=0)&&Buildings.Any(b=>!b.IsHouse&&b.CarparkId==shop.CarparkId&&
                        (Rules.Version==GameVersion.OriginalReference?b.Demand>0:b.Reserved>0));
                    bool longest=Cars.Where(v=>SameCarpark(v.ShopId,shop.Id)&&v.Stage==TripStage.Parking).OrderBy(v=>v.Dwell).FirstOrDefault()==car;
                    bool accessBusy=Cars.Any(v=>v.Id!=car.Id&&SameCarpark(v.ShopId,shop.Id)&&
                        (v.Stage==TripStage.EnteringParking||v.Stage==TripStage.LeavingParking||
                        v.Stage==TripStage.Outbound&&v.CurrentLane!=null&&HasAccess(shop,v.CurrentLane.Tile)));
                    bool finished=Rules.Version==GameVersion.OriginalReference?car.Dwell<0:car.Dwell<=0;
                    if((finished||full&&longest)&&(Rules.Version==GameVersion.OriginalReference?CanBeginBayDeparture(car):!accessBusy))StartLeavingParking(car);
                }
                else if(car.Stage==TripStage.Returning&&!car.Moving)FinishHome(car);
            }
            var snapshot=Cars.Where(c=>c.Moving).Select(c=>new MotionSnapshot{Car=c,Lane=c.CurrentLane,Index=c.RouteIndex,
                Distance=c.DistanceAlongLane,Speed=c.Speed,Acceleration=c.Acceleration,Position=c.Position}).ToList();
            foreach(var state in snapshot)RegisterApproaches(state.Car);
            var proposals=new List<(Vehicle car,double speed,double acceleration,double distance,string obstacle)>();
            foreach(var state in snapshot)
            {
                var car=state.Car;double desired=state.Lane.SpeedLimit,gap=1e6,leaderSpeed=desired,leaderAcceleration=0;
                string obstacle="";double stop=double.PositiveInfinity;
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
                    if(distance<gap){gap=distance;leaderSpeed=other.Speed;leaderAcceleration=other.Acceleration;obstacle="Queue ahead";}
                }
                double aheadDistance=state.Lane.Length-state.Distance;
                for(int i=car.RouteIndex+1;i<Math.Min(car.Lanes.Count,car.RouteIndex+7);i++)
                {
                    var next=car.Lanes[i];
                    if(aheadDistance<Rules.LookaheadDistance)
                    {
                        desired=Math.Min(desired,Math.Sqrt(next.SpeedLimit*next.SpeedLimit+2*Rules.MaxDeceleration*Math.Max(0,aheadDistance-.1)));
                        if(!MayEnter(car,next,snapshot,out string reason))
                        {stop=Math.Min(stop,Math.Max(0,aheadDistance-Rules.CarLength*.35));obstacle=reason;break;}
                    }
                    aheadDistance+=next.Length;if(aheadDistance>Rules.LookaheadDistance)break;
                }
                double remaining=state.Lane.Length-state.Distance;
                for(int i=car.RouteIndex+1;i<car.Lanes.Count;i++)remaining+=car.Lanes[i].Length;
                desired=Math.Min(desired,Math.Sqrt(2*Rules.MaxDeceleration*Math.Max(0,remaining)));
                double acceleration=AccelerationFor(gap,state.Speed,leaderSpeed,leaderAcceleration,Math.Max(.001,desired),
                    state.Lane.IsRoundabout?Rules.RoundaboutAcceleration:state.Lane.IsJunction?Rules.ControlledAcceleration:Rules.MaxAcceleration);
                if(!double.IsInfinity(stop))acceleration=Math.Min(acceleration,AccelerationFor(stop+Rules.CarLength,state.Speed,0,0,desired,Rules.ControlledAcceleration));
                double speed=Math.Max(0,state.Speed+acceleration*Rules.TickSeconds);
                double travel=(state.Speed+speed)*.5*Rules.TickSeconds;
                // Hard clearance bounds are independent of acceleration integration and tick ordering.
                travel=Math.Min(travel,Math.Max(0,gap-Rules.CarLength-Rules.FollowingGap));
                travel=Math.Min(travel,stop);
                if(travel<=1e-7){speed=0;if(obstacle.Length==0)obstacle="Driveway queue";}
                proposals.Add((car,speed,acceleration,Math.Max(0,travel),obstacle));
            }
            foreach(var proposal in proposals)
            {
                var car=proposal.car;double travel=proposal.distance;
                if(Rules.Version==GameVersion.OriginalReference&&NearCarpark(car))
                {
                    bool Clear(double distance)
                    {
                        PoseAlongJourney(car,distance,out var position,out var heading);
                        return !Cars.Any(other=>other.Id!=car.Id&&NearCarpark(other)&&SameCarpark(car.ShopId,other.ShopId)&&
                            Point.Distance(position,other.Position)<Rules.CarLength+.2&&
                            VehicleBodiesOverlap(position,heading,other.Position,other.Heading));
                    }
                    if(travel>0&&!Clear(travel))
                    {
                        double lo=0,hi=travel;for(int i=0;i<10;i++){double mid=(lo+hi)/2;if(Clear(mid))lo=mid;else hi=mid;}
                        travel=lo;
                    }
                }
                car.Speed=travel<proposal.distance-1e-8?0:proposal.speed;car.Acceleration=proposal.acceleration;
                car.Obstacle=travel<proposal.distance-1e-8?"Carpark lane clearance":proposal.obstacle;car.WaitingAtSignal=car.Obstacle=="Traffic light";
                car.WaitingAtIntersection=car.Obstacle.Contains("priority")||car.Obstacle.Contains("Crossing")||car.Obstacle.Contains("yield");
                if(car.Speed<.02&&car.Stage!=TripStage.Parking){car.Waiting+=Rules.TickSeconds;car.TotalWaiting+=Rules.TickSeconds;}else car.Waiting=0;
                AdvanceVehicle(car,travel);
            }
        }

        bool NearCarpark(Vehicle car)=>car.ShopId>=0&&(car.Stage==TripStage.Parking||car.Moving&&
            (car.CurrentLane.IsParking||HasAccess(Buildings[car.ShopId],car.CurrentLane.Tile)||HasAccess(Buildings[car.ShopId],car.CurrentLane.Next)));

        bool CanBeginBayDeparture(Vehicle car)
        {
            var shop=Buildings[car.ShopId];
            var launch=ParkingRoute(shop,car.DestinationAccess,car.ParkingSlot,true).Take(2).ToArray();
            foreach(var other in Cars.Where(v=>v.Id!=car.Id&&SameCarpark(v.ShopId,car.ShopId)&&v.Moving))
                foreach(var lane in other.Lanes.Skip(other.RouteIndex).Where(l=>l.IsParking))
                    foreach(var own in launch)
                        for(int i=0;i<own.Samples.Length;i++)for(int j=0;j<lane.Samples.Length;j++)
                        {
                            if(lane==other.CurrentLane&&lane.Distances[j]<other.DistanceAlongLane)continue;
                            if(Point.Distance(own.Samples[i],lane.Samples[j])<Rules.CarLength+.025)return false;
                        }
            return true;
        }

        void PoseAlongJourney(Vehicle car,double distance,out Point position,out Point heading)
        {
            int index=car.RouteIndex;distance+=car.DistanceAlongLane;
            while(index<car.Lanes.Count-1&&distance>car.Lanes[index].Length){distance-=car.Lanes[index].Length;index++;}
            var lane=car.Lanes[index];distance=Math.Min(distance,lane.Length);
            position=lane.Position(distance);heading=lane.Tangent(distance);
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

        public double AccelerationFor(double centerGap,double speed,double leadingSpeed,double leadingAcceleration,double desired,double maximumAcceleration)
        {
            // Independently expressed car-following equations matching the recovered reference model.
            if(desired<1e-6)return -Rules.MaxDeceleration;
            double space=Math.Max(centerGap-Rules.CarLength,Rules.FollowingGap),relative=speed-leadingSpeed;
            double free=speed<=desired?maximumAcceleration*(1-Math.Pow(speed/desired,4)):
                -Rules.MaxDeceleration*(1-Math.Pow(desired/Math.Max(.001,speed),maximumAcceleration*6/Rules.MaxDeceleration));
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
                car.RouteIndex++;car.DistanceAlongLane=0;car.SegmentEntered=Time;
                if(car.RouteIndex>=car.Lanes.Count){FinishJourney(car);break;}
                RefreshJourney(car);
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
                    Deliver(car);
                    if(car.DrivingThrough){car.Stage=TripStage.Returning;SetJourney(car,car.ReturnRoute);break;}
                    car.Stage=TripStage.Parking;car.ParkedPosition=ParkingPoint(Buildings[car.ShopId],car.ParkingSlot);
                    car.ParkedHeading=Rules.Version==GameVersion.OriginalReference?ParkingHeading(Buildings[car.ShopId],car.DestinationAccess):new Point(0,-1);
                    car.Dwell=Rules.ServiceSeconds;break;
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
                {car.Stage=TripStage.EnteringParking;car.Lanes=ParkingDriveThrough(shop,car.DestinationAccess);car.RouteIndex=0;car.DistanceAlongLane=0;return;}
                Deliver(car);car.Stage=TripStage.Returning;SetJourney(car,car.ReturnRoute);return;
            }
            int slot=available.Count==1?available[0]:available[random.Next(available.Count)];
            car.ParkingSlot=slot;shop.Parking[slot]=car.Id;car.Stage=TripStage.EnteringParking;
            if(Rules.Version==GameVersion.OriginalReference)
            {car.Lanes=ParkingRoute(shop,car.DestinationAccess,slot);car.RouteIndex=0;car.DistanceAlongLane=0;return;}
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
                car.Lanes=ParkingRoute(destination,car.DestinationAccess,car.ParkingSlot,true);car.Stage=TripStage.LeavingParking;car.RouteIndex=0;car.DistanceAlongLane=0;car.Speed=0;return;
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
            car.Stage=TripStage.Home;car.At=Buildings[car.HomeId].Cell;car.Next=car.At;car.Lanes.Clear();car.Route.Clear();
            car.ReturnRoute.Clear();car.ApproachRegistered.Clear();car.ShopId=-1;car.Speed=0;car.ArrivedHome=Time;car.RouteIndex=0;car.DistanceAlongLane=0;car.Obstacle="";
        }
    }
}
