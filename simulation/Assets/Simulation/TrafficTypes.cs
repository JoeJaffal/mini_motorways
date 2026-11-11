using System;
using System.Collections.Generic;
using System.Linq;

namespace MotorwaysSim
{
    public readonly struct Cell : IEquatable<Cell>, IComparable<Cell>
    {
        public readonly int X, Y;
        public Cell(int x,int y){X=x;Y=y;}
        public bool Equals(Cell p)=>X==p.X&&Y==p.Y;
        public override bool Equals(object p)=>p is Cell q&&Equals(q);
        public override int GetHashCode()=>unchecked(X*397^Y);
        public int CompareTo(Cell p)=>Y!=p.Y?Y.CompareTo(p.Y):X.CompareTo(p.X);
        public static bool operator ==(Cell a,Cell b)=>a.Equals(b);
        public static bool operator !=(Cell a,Cell b)=>!a.Equals(b);
        public static Cell operator +(Cell a,Cell b)=>new Cell(a.X+b.X,a.Y+b.Y);
        public override string ToString()=>$"({X}, {Y})";
    }

    public readonly struct Point
    {
        public readonly double X,Y;
        public Point(double x,double y){X=x;Y=y;}
        public Point(Cell p){X=p.X+.5;Y=p.Y+.5;}
        public double Length=>Math.Sqrt(X*X+Y*Y);
        public Point Unit=>Length<1e-9?new Point(1,0):this/Length;
        public Point Right=>new Point(-Y,X);
        public static Point operator +(Point a,Point b)=>new Point(a.X+b.X,a.Y+b.Y);
        public static Point operator -(Point a,Point b)=>new Point(a.X-b.X,a.Y-b.Y);
        public static Point operator *(Point a,double b)=>new Point(a.X*b,a.Y*b);
        public static Point operator /(Point a,double b)=>new Point(a.X/b,a.Y/b);
        public static double Dot(Point a,Point b)=>a.X*b.X+a.Y*b.Y;
        public static double Distance(Point a,Point b)=>(a-b).Length;
        public static Point Lerp(Point a,Point b,double t)=>a+(b-a)*t;
    }

    public enum Infrastructure {None,Road,Bridge,Roundabout,TrafficLight}
    public enum BuildTool {Road,Bridge,Roundabout,TrafficLight,Remove,Motorway}
    public enum TripStage {Home,Outbound,EnteringParking,Parking,LeavingParking,Returning,AligningHome}
    public enum ObstacleKind {None,Leader,BlockingJunction,RouteEnd}
    public enum ScenarioKind {LosAngeles,ReferenceLab,EmptyLab,Beijing,Tokyo,DarEsSalaam,London}
    public enum GameVersion {OriginalReference,Custom}
    public enum MapVariation {SameMap,DifferentMaps}

    [Serializable]
    public sealed class Rules
    {
        public GameVersion Version=GameVersion.Custom;
        public bool RejectInfeasibleScenarios=true;
        public bool UnlimitedConstruction=true;
        public static Rules ForVersion(GameVersion version)
        {
            return new Rules {Version=version,RoadCost=version==GameVersion.Custom?2:0,
                LightCost=version==GameVersion.Custom?5:0,BridgeCost=version==GameVersion.Custom?10:0,RoundaboutCost=version==GameVersion.Custom?8:0,
                EnforceFeasibility=false,RejectInfeasibleScenarios=version==GameVersion.Custom,
                ConstructionGraceSeconds=version==GameVersion.Custom?30:0,UnlimitedConstruction=version==GameVersion.Custom};
        }
        public double TickSeconds=.05;
        public double MotorwaySpeed=1.5; // Reference lane value3 converted for tile width2; not the final movement target.
        // Original world units have tile width2; motion multiplies the converted lane value by its separate reference factor.
        public double MovementSpeedMultiplier=>Version==GameVersion.OriginalReference?3:1;
        public double CarSpeed=.5,MaxAcceleration=.27,ControlledAcceleration=.4,RoundaboutAcceleration=.45;
        public double MaxDeceleration=6,FollowingGap=.05,CarLength=.325,DesiredTimeGap=1;
        public double LaneOffset=.1,SharpTurnMultiplier=1.0/3,RightAngleMultiplier=2.0/3;
        public double IntersectionMultiplier=.5,RoundaboutMultiplier=1.2,LookaheadDistance=2.5;
        public double ServiceSeconds=3,HomeCooldown=0;
        public double SignalGreenSeconds=3,SignalOvertimeSeconds=1,SignalAmberSeconds=.7;
        public double SignalNearbyDistance=.5,SignalMaxWaitingWeightSeconds=30,MaximumIntersectionWait=45;
        public int SignalMinimumNearbyCars=3;
        public double SecondsPerDay=20,SecondsPerWeek=140;
        public double AverageCarsPerDay=1.55,DemandMultiplier=.8,FirstDemandDelay=4;
        public double OvercrowdingSeconds=50,OvercrowdingGraceSeconds=2,OvercrowdingAcceleration=1,OvercrowdingReturnSpeed=2;
        public double ArrivalTimerDeceleration=.02,ArrivalTimerReductionFraction=.1,ArrivalTimerReductionMax=3;
        public int DemandCapacity=6,MaximumOverflowPins=4,CarsPerHouse=2,ParkingSpaces=6;
        public int RoadCost=2,LightCost=5,BridgeCost=10,RoundaboutCost=8;
        // Provisional safeguards/defaults, explicitly separate from recovered original constants.
        public bool EnforceFeasibility=false,EnableCityGrowth=true,UseOriginalIntersectionRules=true;
        public double CapacitySafetyFactor=.65,ConstructionGraceSeconds=30,HouseSpawnInterval=20;
        public int MaxShops=30;
    }

    public sealed class Building
    {
        public int Id,Color;
        public Cell Cell,Entrance;
        public bool IsHouse,SharedLot,IsStation;
        public int CarparkId=-1,DestinationSlot;
        public Cell[] Entrances=new Cell[0],Platform=new Cell[0];public int[] EntranceDirections=new int[0];
        public int Width=1,Height=1,DrivewayDirection,Layout;
        public bool Upgraded;public double UpgradeAt=double.PositiveInfinity,PlannedDemandMultiplier=1;
        public int Demand,Reserved,DemandJustCleared;
        public double NextDemand,OvercrowdedFor,OvercrowdingSpeed,SpawnTime,SpawnGraceUntil,Served;
        public double OriginalDemandInterval,FeasibleDemandInterval,LastFeasibilityCheck;
        public double DemandPhase,DemandCountdown;
        public double MaximumPotentialArrivalRate,SupplyBoundCheckedAt=-100;
        public int SupplyBoundBuildingCount=-1;
        public bool FeasibilityVerified;
        public int[] Parking;
        public List<Cell> FeasibilityRoute=new List<Cell>();
        public Cell Access=>IsHouse?Cell:Entrance;
        public bool Contains(Cell c)=>c.X>=Cell.X&&c.X<Cell.X+Width&&c.Y>=Cell.Y&&c.Y<Cell.Y+Height;
    }

    public sealed class Lane
    {
        public Cell Tile,Previous,Next;
        public int Incoming,Outgoing;
        public Point[] Samples;
        public double[] Distances;
        public double Length,SpeedLimit;
        public bool IsJunction,IsRoundabout,IsParking,IsMotorway,ReleasesParking,DeliversDriveThrough,IsCorner;
        public string Chunk=""; // carpark lanes: "carpark:<id>:<chunk>" (CarparkArbitration.cs)
        public Cell? Corner; // corner lanes (OriginalReference): code cell of the tile corner chunk they belong to
        public Cell ChunkCell=>Corner??Tile; // the road chunk whose lanes arbitrate with this one
        public int MotorwayId=-1;
        public int CarparkId=-1;
        public string Key;
        public Point Position(double distance)
        {
            if(Samples==null||Samples.Length==0)return new Point(Tile);
            if(distance<=0)return Samples[0];if(distance>=Length)return Samples[Samples.Length-1];
            int lo=0,hi=Distances.Length-1;
            while(hi-lo>1){int mid=(lo+hi)/2;if(Distances[mid]<distance)lo=mid;else hi=mid;}
            return Point.Lerp(Samples[lo],Samples[hi],(distance-Distances[lo])/Math.Max(1e-9,Distances[hi]-Distances[lo]));
        }
        public Point Tangent(double distance)=>(Position(Math.Min(Length,distance+.01))-Position(Math.Max(0,distance-.01))).Unit;
    }

    public sealed class Vehicle
    {
        public int Id,HomeId,ShopId=-1,Color,ParkingSlot=-1;
        public TripStage Stage;
        public Cell At,Next,DestinationAccess;
        public double Progress,Dwell,Waiting,TotalWaiting,Speed,Acceleration,DistanceAlongLane,ArrivedHome;
        public double JourneyStarted,LastMoved,SegmentEntered;
        public List<Cell> Route=new List<Cell>(),ReturnRoute=new List<Cell>();
        public List<Lane> Lanes=new List<Lane>();
        public int RouteIndex,RouteVersion;
        public bool HasDelivered,WaitingAtSignal,WaitingAtIntersection,DrivingThrough;
        public string Obstacle="";
        public readonly Dictionary<string,double> ApproachRegistered=new Dictionary<string,double>();
        // Original junction arbitration state (JunctionArbitration.cs): the previous tick's nearest
        // obstacle, and the blocking-cycle shove permission for one immediate next lane.
        public ObstacleKind ObstacleState;public int ObstacleCar=-1;public double ObstacleDistance;
        public int BlockingVehicle=-1; // original blockingVehicle: the leader, or the vehicle refusing its junction entry
        public bool Shoving;public string ShovingLane="";
        public int PushingInto=-1; // original vehiclePushingInto: leader this car pushes into while their all-leader cycle lasts
        // Tile of the junction lane this car was refused at (BlockingJunction), and the game time each planned
        // lane first entered the first-two-remaining-lanes commitment window (original signal weights).
        public Cell BlockingTile;public readonly Dictionary<string,double> CommittedAt=new Dictionary<string,double>();
        public Point ParkedPosition,ParkedHeading=new Point(0,-1);
        // Continuous journeys (OriginalReference, ContinuousJourneys.cs): index of the carpark entrance lane at the
        // end of an outbound path, whether the in-lot lanes are attached, and lane indices where the stage changes.
        public int ParkingLegAt=-1;public bool ParkingLegAttached;
        public readonly List<(int Index,TripStage Stage)> LegMarks=new List<(int Index,TripStage Stage)>();
        public bool Moving=>Lanes.Count>0&&RouteIndex<Lanes.Count;
        public Lane CurrentLane=>Moving?Lanes[RouteIndex]:null;
        public Point Position=>Stage==TripStage.Parking?ParkedPosition:CurrentLane?.Position(DistanceAlongLane)??new Point(At);
        public Point Heading=>Stage==TripStage.Parking?ParkedHeading:CurrentLane?.Tangent(DistanceAlongLane)??new Point(1,0);
    }

    public sealed class SignalState
    {
        public Cell Cell;
        public List<int> Pairs=new List<int>();
        public int ActivePair;
        public double Elapsed;
        public bool Amber,Overtime;
    }

    public sealed class RoundaboutState
    {
        public Cell Center;
        public Cell[] Ring;
        public bool PendingRemoval;
        // OriginalReference: placed but not yet hot-swapped (RoundaboutActivation.cs), with the footprint's road counts from
        // before the circle for arbitration among cars still on the replaced lanes.
        public bool Planned;public Dictionary<Cell,int> PlannedDegrees;
        // Concrete replaced by the circle stays reserved until old surface lanes clear.
        public int ReplacedRoadTiles;
    }

    public sealed class MotorwayState
    {public int Id,Number;public Cell Start,End;public bool PendingRemoval,RefundOnRemoval=true;public int StartDirection=-1,EndDirection=-1;public Cell Other(Cell c)=>c==Start?End:Start;}
    public sealed class MotorwaySnapshot
    {public int Id,Number;public Cell Start,End;public bool PendingRemoval;}

    public sealed class ConstructionEvent
    {public double Time;public Cell Cell;public BuildTool Tool;public int Cost;public string Description;}

    public sealed class Observation
    {
        public int Width,Height,ConstructionSpent,TripsCompleted,Day,Week,Hour;
        public double Time,DisconnectedColorComponents,MeanWaiting;
        public bool Failed,ScenarioRejected,UnlimitedConstruction,ExactReplicaValidated;
        public string FidelityStatus;
        public int RoadCost,LightCost,BridgeCost,RoundaboutCost;
        public double ConstructionGraceSeconds;
        public string Scenario,ProvisionalDefaults,Version,RejectionReason,Objective,Variation;
        public int RoadTilesAvailable;public int[] Inventory;public UpgradeOffer[] UpgradeChoices;
        public int[] Infrastructure,Terrain,BuildingColors,BuildingKinds,Demand,Reservations,Connections,PendingRemovals;
        public VehicleState[] Vehicles;
        public BuildingState[] Buildings;
        public ScheduledSpawnSnapshot[] ScheduledSpawns;
        public string RandomAlgorithm;public long RandomDraws;
        public SignalSnapshot[] Signals;
        public RoundaboutSnapshot[] Roundabouts;
        public MotorwaySnapshot[] Motorways;
        public TrainSnapshot[] Trains;public RailSnapshot[] RailLines;public Cell[] ClosedRailCrossings;
        public double PlayableXMin,PlayableYMin,PlayableXMax,PlayableYMax;
    }
    public sealed class VehicleState
    {
        public int Id,HomeId,ShopId,Color,ParkingSlot;public TripStage Stage;
        public Cell At,Next;public double X,Y,HeadingX,HeadingY,Speed,Acceleration,Waiting,Progress;
        public string Obstacle;public Cell[] Route,ReturnRoute;
    }
    public sealed class BuildingState
    {
        public int Id,Color,Width,Height,Demand,Reserved,DrivewayDirection,Layout,DemandCapacity;public Cell Cell,Entrance;public bool IsHouse,FeasibilityVerified,Upgraded,SharedLot,IsStation;
        public int CarparkId,DestinationSlot;public Cell[] Entrances,Platform;public int[] EntranceDirections;
        public double? UpgradeAt;public double PlannedDemandMultiplier;
        public double OvercrowdedFor,OriginalDemandInterval;public double? FeasibleDemandInterval;public int[] Parking;
    }
    public sealed class SignalSnapshot
    {public Cell Cell;public int ActivePair;public bool Amber;public double Elapsed;public int[] Pairs;}
    public sealed class RoundaboutSnapshot
    {public Cell Center;public Cell[] Ring;public bool PendingRemoval;public bool Planned; /* OriginalReference: placed, not yet active */}
}
