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
            lane.Key="carpark:"+shop.CarparkId+":"+key;lane.CarparkId=shop.CarparkId;lane.IsParking=true;lane.ReleasesParking=release;lane.SpeedLimit=Rules.CarSpeed*.6;
            return lane;
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
        public List<Lane> ParkingRoute(Building shop,Cell access,int slot,bool leaving=false)
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
                var end=left?bay.InnerBay:bay.OuterBay;
                lanes.Add(ParkingCurve(shop,"bay-leave:"+slot+":"+left,bay.Center,bay.Center,end,end,release:true,straight:true));
                if(left)lanes.Add(ParkingCurve(shop,"bay-inner-out:"+slot,bay.InnerBay,bay.InnerBay-normal*.15,bay.InnerEnd+axis*.1,bay.InnerEnd));
                else lanes.Add(ParkingCurve(shop,"bay-outer-out:"+slot,bay.OuterBay,bay.OuterBay+normal*.15,bay.OuterEnd-axis*.1,bay.OuterEnd));
                if(left)for(int i=slot-1;i>=0;i--)lanes.Add(ParkingThroughBay(shop,i,false));
                else for(int i=slot+1;i<shop.Parking.Length;i++)lanes.Add(ParkingThroughBay(shop,i,true));
                lanes.Add(ParkingConnector(shop,access,false));
            }
            return lanes;
        }
        public List<Lane> ParkingDriveThrough(Building shop,Cell access)
        {
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
