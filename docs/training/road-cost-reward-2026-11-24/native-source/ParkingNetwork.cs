using System;
using System.Collections.Generic;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        struct ParkingBayGeometry
        {public Point OuterStart,OuterEnd,InnerStart,InnerEnd,OuterBay,InnerBay,Center;}
        public Point ParkingAccessPoint(Building shop,Cell access,bool entering)
        {
            var step=Directions[AccessDirection(shop,access)];var outward=new Point(step.X,step.Y);
            return new Point(access)+outward*.5+(entering?outward*-1:outward).Right*Rules.LaneOffset;
        }

        void ParkingAxes(Building shop,out Point axis,out Point side,out Point diagonal,out Point anchor)
        {
            bool horizontal=shop.Layout<2,top=shop.SharedLot&&shop.Layout==1,right=shop.SharedLot&&shop.Layout==3;
            axis=horizontal?new Point(1,0):new Point(0,1);
            side=horizontal?new Point(0,1):new Point(-1,0);
            diagonal=horizontal?new Point(1,-1):new Point(1,1);
            anchor=horizontal?new Point(shop.Cell.X+.5,shop.Cell.Y+(top?.5:2.5)):
                new Point(shop.Cell.X+(right?2.5:.5),shop.Cell.Y+.5);
            // Recovered bay pitch, side adjustment and diagonal layout, in tile units.
            anchor+=side*(1.0/6+(top||right?.05:-.05));
        }
        ParkingBayGeometry ParkingBay(Building shop,int index)
        {
            ParkingAxes(shop,out var axis,out var side,out var diagonal,out var anchor);
            var p=anchor+axis*(index/3.0);var offset=diagonal/3;
            return new ParkingBayGeometry{
                OuterStart=p-diagonal*.125-axis/15-(index==0?side*.125:new Point()),
                OuterEnd=p-diagonal*.125+axis*(4.0/15),
                InnerStart=p+offset+diagonal*.125+axis/15+(index==shop.Parking.Length-1?side*.125:new Point()),
                InnerEnd=p+offset+diagonal*.125-axis*(4.0/15),
                OuterBay=p+offset*.3,InnerBay=p+offset*.7,Center=p+offset*.5};
        }
        public Point ParkingHeading(Building shop,Cell access)
        {
            ParkingAxes(shop,out _,out _,out var diagonal,out _);
            return diagonal.Unit*(AccessDirection(shop,access)==4||AccessDirection(shop,access)==6?1:-1);
        }
        Lane ParkingCurve(Building shop,string key,Point a,Point b,Point c,Point d,bool release=false,bool straight=false)
        {
            var lane=CreateLane(straight?new[]{a,d}:Cubic(a,b,c,d,10),shop.Entrance,shop.Entrance,shop.Entrance,0,0);
            lane.Key="carpark:"+shop.CarparkId+":"+key;lane.Chunk="carpark:"+shop.CarparkId+":"+ParkingChunkName(key);lane.CarparkId=shop.CarparkId;lane.IsParking=true;lane.ReleasesParking=release;
            lane.SpeedLimit=Rules.Version==GameVersion.OriginalReference?Rules.CarSpeed*OriginalParkingLaneFactor(shop,key):Rules.CarSpeed*.6;
            if(Rules.Version==GameVersion.OriginalReference)SetParkingNodes(shop,key,lane);
            return lane;
        }
        // Original CarparkModel: each bay's outer and inner aisle chunks hold a through lane, a bay entry and a bay exit
        // whose connections run between the aisle sides (backward B, forward F along the lot axis) and the bay node
        // (the outer chunk's bay node is F turned 45 degrees counter-clockwise, the inner chunk's the opposite).
        // Incoming is the travel direction on entry (entry side + 4), Outgoing the exit side, as for road lanes.
        void SetParkingNodes(Building shop,string key,Lane lane)
        {
            ParkingAxes(shop,out var axis,out _,out var diagonal,out _);
            int F=DirectionOf(axis),B=(F+4)%8,bayO=DirectionOf(diagonal),bayI=(bayO+4)%8;
            string kind=key.Split(':')[0];int inSide,outSide;
            switch(kind)
            {
                case "outer":inSide=B;outSide=F;break;
                case "bay-outer-in":inSide=B;outSide=bayO;break;
                case "bay-outer-out":inSide=bayO;outSide=F;break;
                case "inner":inSide=F;outSide=B;break;
                case "bay-inner-in":inSide=F;outSide=bayI;break;
                case "bay-inner-out":inSide=bayI;outSide=B;break;
                // Lot ends: the first end's aisles lie on its F side and its road on the B side, the last end the reverse.
                // U-turn F->F (first) / B->B (last); entrance road->aisle; exit aisle->road.
                case "turn-first":inSide=F;outSide=F;break;
                case "turn-last":inSide=B;outSide=B;break;
                case "entrance":if(key.EndsWith("first")){inSide=B;outSide=F;}else{inSide=F;outSide=B;}break;
                case "exit":if(key.EndsWith("first")){inSide=F;outSide=B;}else{inSide=B;outSide=F;}break;
                default:return;
            }
            lane.Incoming=(inSide+4)%8;lane.Outgoing=outSide;lane.ParkingNodes=true;
        }
        static int DirectionOf(Point v)
        {
            int best=0;double score=double.NegativeInfinity;var u=v.Unit;
            for(int d=0;d<8;d++){var w=new Point(Directions[d].X,Directions[d].Y).Unit;double s=u.X*w.X+u.Y*w.Y;if(s>score+1e-9){score=s;best=d;}}
            return best;
        }
        // The original's GetLaneSpeed applied to its carpark lanes (CarparkModel): default speed times the turn factor
        // (45 degrees: 1, sharp/U-turn: 1/3) times the intersection factor 0.5 when the lane leads to more than one lane.
        double OriginalParkingLaneFactor(Building shop,string key)
        {
            bool left=false,right=false;
            foreach(var access in Accesses(shop)){int d=AccessDirection(shop,access);if(d==4||d==6)left=true;else right=true;}
            string[] parts=key.Split(':');int index=parts.Length>1&&int.TryParse(parts[1],out int value)?value:-1;int last=shop.Parking.Length-1;
            switch(parts[0])
            {
                case "entrance":return .5;                                  // straight, then bay entry or through aisle
                case "exit":return 1;                                       // straight onto the road
                case "turn-first":case "turn-last":return 1.0/3;            // U-turn at a lot end
                case "outer":return index==last&&!right?1:.5;               // straight; next bay's entry and through lane
                case "inner":return index==0&&!left?1:.5;
                case "bay-outer-in":case "bay-inner-in":return 1;           // 45-degree turn into the bay
                case "bay-park":case "bay-leave":return 1;                  // straight across the bay
                case "bay-outer-out":return 1.0/3*(index==last&&!right?1:.5); // sharp turn onto the aisle
                case "bay-inner-out":return 1.0/3*(index==0&&!left?1:.5);
                default:return .6;
            }
        }
        Lane ParkingThroughBay(Building shop,int index,bool outer)
        {
            ParkingAxes(shop,out var axis,out var side,out _,out _);var bend=(axis*-1-side).Unit;var bay=ParkingBay(shop,index);
            if(outer)return ParkingCurve(shop,"outer:"+index,bay.OuterStart,bay.OuterStart-bend*.15,bay.OuterEnd-axis*.1,bay.OuterEnd,straight:index!=0);
            return ParkingCurve(shop,"inner:"+index,bay.InnerStart,bay.InnerStart+bend*.15,bay.InnerEnd+axis*.1,bay.InnerEnd,straight:index!=shop.Parking.Length-1);
        }
        Lane ParkingConnector(Building shop,Cell access,bool entering)
        {
            ParkingAxes(shop,out var axis,out var side,out _,out _);var bend=(axis*-1-side).Unit;
            bool left=AccessDirection(shop,access)==4||AccessDirection(shop,access)==6;
            var bay=ParkingBay(shop,left?0:shop.Parking.Length-1);var end=ParkingAccessPoint(shop,access,entering);
            string key=(entering?"entrance:":"exit:")+(left?"first":"last");
            // Join the surface boundary to the physical internal circulation lanes.
            Lane connector;
            if(entering)connector=left?ParkingCurve(shop,key,end,end+axis*.1,bay.OuterStart+bend*.05,bay.OuterStart):
                ParkingCurve(shop,key,end,end-axis*.1,bay.InnerStart-bend*.1,bay.InnerStart);
            else connector=left?ParkingCurve(shop,key,bay.InnerEnd,bay.InnerEnd-axis*.5,end+axis*.375,end):
                ParkingCurve(shop,key,bay.OuterEnd,bay.OuterEnd+axis*.5,end-axis*.375,end);
            connector.Tile=access;connector.Previous=access;connector.Next=access;return connector;
        }
        // enteredLeft (leaving only): the side the car parked from. The original's bay lanes are one-way across the
        // bay (outer to inner for the first entrance, inner to outer for the last), so a car leaving by the other
        // entrance first follows its own side's aisle to the lot end, U-turns, and drives the whole other aisle.
        public List<Lane> ParkingRoute(Building shop,Cell access,int slot,bool leaving=false,bool? enteredLeft=null)
        {
            if(slot<0||slot>=shop.Parking.Length||!HasAccess(shop,access))throw new ArgumentException("Invalid parking bay or entrance");
            ParkingAxes(shop,out var axis,out var side,out var diagonal,out _);
            var normal=diagonal.Unit*-1;var bend=(axis*-1-side).Unit;var bay=ParkingBay(shop,slot);
            bool left=AccessDirection(shop,access)==4||AccessDirection(shop,access)==6;
            var lanes=new List<Lane>();
            if(!leaving)
            {
                lanes.Add(ParkingConnector(shop,access,true));
                if(left)for(int i=0;i<slot;i++)lanes.Add(ParkingThroughBay(shop,i,true));
                else for(int i=shop.Parking.Length-1;i>slot;i--)lanes.Add(ParkingThroughBay(shop,i,false));
                if(left)lanes.Add(ParkingCurve(shop,"bay-outer-in:"+slot,bay.OuterStart,bay.OuterStart+(slot==0?bend*-1:axis)*.1,bay.OuterBay+normal*.1,bay.OuterBay));
                else lanes.Add(ParkingCurve(shop,"bay-inner-in:"+slot,bay.InnerStart,bay.InnerStart-(slot==shop.Parking.Length-1?bend*-1:axis)*.1,bay.InnerBay-normal*.1,bay.InnerBay));
                var a=left?bay.OuterBay:bay.InnerBay;
                lanes.Add(ParkingCurve(shop,"bay-park:"+slot+":"+left,a,a,bay.Center,bay.Center,straight:true));
            }
            else
            {
                bool from=enteredLeft??left;int last=shop.Parking.Length-1;
                var end=from?bay.InnerBay:bay.OuterBay;
                lanes.Add(ParkingCurve(shop,"bay-leave:"+slot+":"+from,bay.Center,bay.Center,end,end,release:true,straight:true));
                if(from)lanes.Add(ParkingCurve(shop,"bay-inner-out:"+slot,bay.InnerBay,bay.InnerBay-normal*.15,bay.InnerEnd+axis*.1,bay.InnerEnd));
                else lanes.Add(ParkingCurve(shop,"bay-outer-out:"+slot,bay.OuterBay,bay.OuterBay+normal*.15,bay.OuterEnd-axis*.1,bay.OuterEnd));
                if(from)for(int i=slot-1;i>=0;i--)lanes.Add(ParkingThroughBay(shop,i,false));
                else for(int i=slot+1;i<=last;i++)lanes.Add(ParkingThroughBay(shop,i,true));
                if(from!=left)
                {
                    var turn=ParkingBay(shop,from?0:last);
                    lanes.Add(from?ParkingCurve(shop,"turn-first",turn.InnerEnd,turn.InnerEnd-axis*.15,turn.OuterStart+bend*.35,turn.OuterStart):
                        ParkingCurve(shop,"turn-last",turn.OuterEnd,turn.OuterEnd+axis*.15,turn.InnerStart-bend*.35,turn.InnerStart));
                    if(from)for(int i=0;i<=last;i++)lanes.Add(ParkingThroughBay(shop,i,true));
                    else for(int i=last;i>=0;i--)lanes.Add(ParkingThroughBay(shop,i,false));
                }
                lanes.Add(ParkingConnector(shop,access,false));
            }
            return lanes;
        }
        public List<Lane> ParkingDriveThrough(Building shop,Cell access)
        {
            if(Rules.Version==GameVersion.OriginalReference)
            {
                // Original ParkVehiclesProcess: a car finding no free bay paths home from the entrance over every lane,
                // carpark lanes at double cost, so the cheapest way out crosses the bay nearest the entrance (behind the
                // car parked there) rather than lapping the lot.
                bool near=AccessDirection(shop,access)==4||AccessDirection(shop,access)==6;int slot=near?0:shop.Parking.Length-1;
                var through=ParkingRoute(shop,access,slot);through[0].DeliversDriveThrough=true;
                through.AddRange(ParkingRoute(shop,access,slot,true));return through;
            }
            ParkingAxes(shop,out var axis,out var side,out _,out _);var bend=(axis*-1-side).Unit;
            bool left=AccessDirection(shop,access)==4||AccessDirection(shop,access)==6;
            var lanes=new List<Lane>{ParkingConnector(shop,access,true)};lanes[0].DeliversDriveThrough=true;
            if(left)for(int i=0;i<shop.Parking.Length;i++)lanes.Add(ParkingThroughBay(shop,i,true));
            else for(int i=shop.Parking.Length-1;i>=0;i--)lanes.Add(ParkingThroughBay(shop,i,false));
            var bay=ParkingBay(shop,left?shop.Parking.Length-1:0);
            lanes.Add(left?ParkingCurve(shop,"turn-last",bay.OuterEnd,bay.OuterEnd+axis*.15,bay.InnerStart-bend*.35,bay.InnerStart):
                ParkingCurve(shop,"turn-first",bay.InnerEnd,bay.InnerEnd-axis*.15,bay.OuterStart+bend*.35,bay.OuterStart));
            if(left)for(int i=shop.Parking.Length-1;i>=0;i--)lanes.Add(ParkingThroughBay(shop,i,false));
            else for(int i=0;i<shop.Parking.Length;i++)lanes.Add(ParkingThroughBay(shop,i,true));
            lanes.Add(ParkingConnector(shop,access,false));return lanes;
        }
    }
}
