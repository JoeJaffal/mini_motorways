using System;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        double startOffsetX,startOffsetY,boundsTime=double.NaN;
        readonly double[] playableBounds=new double[4];
        public double[] PlayableBounds {get{UpdatePlayableBounds();return (double[])playableBounds.Clone();}}
        void InitializePlayableArea()
        {
            startOffsetX=0;startOffsetY=0;boundsTime=double.NaN;
            if(Rules.Version!=GameVersion.OriginalReference||!Array.Exists(CityCatalog.Maps,m=>m==Scenario)||Map.StartOffsets.Length==0)return;
            var offset=Map.StartOffsets[random.Next(Map.StartOffsets.Length)];
            startOffsetX=offset[0];startOffsetY=offset[1];
            // Selection/variance sampling is provisional until original random streams are matched.
            if(offset.Length>2&&offset[2]>0){startOffsetX+=(random.NextDouble()*2-1)*offset[2];startOffsetY+=(random.NextDouble()*2-1)*offset[2];}
        }
        public double[] ViewBounds
        {
            get
            {
                if(customScenarioBounds!=null)return (double[])customScenarioBounds.Clone();
                if(Rules.Version!=GameVersion.OriginalReference||!Array.Exists(CityCatalog.Maps,m=>m==Scenario))return new double[]{0,0,Width,Height};
                double size=CityZoom,progress=Math.Max(0,Math.Min(1,(size-Map.Zoom[0])/(Map.Zoom[1]-Map.Zoom[0])));
                double cx=25.5+startOffsetX*(1-progress),cy=14.5-startOffsetY*(1-progress);
                return new[]{cx-size*8/9,cy-size/2,cx+size*8/9,cy+size/2};
            }
        }
        public double CityZoom
        {
            get
            {
                double days=Time/Rules.SecondsPerDay;
                if(days<=Map.Zoom[2])return Map.Zoom[0];
                if(days>=Map.Zoom[2]+Map.Zoom[3])return Map.Zoom[1];
                return EvaluateCurve(Map.ZoomCurve,days);
            }
        }
        static double EvaluateCurve(double[][] keys,double time)
        {
            if(time<=keys[0][0])return keys[0][1];
            for(int i=1;i<keys.Length;i++)
            {
                if(time>keys[i][0])continue;
                var a=keys[i-1];var b=keys[i];double dt=b[0]-a[0],t=(time-a[0])/dt,t2=t*t,t3=t2*t;
                return (2*t3-3*t2+1)*a[1]+(t3-2*t2+t)*dt*a[3]+(-2*t3+3*t2)*b[1]+(t3-t2)*dt*b[2];
            }
            return keys[keys.Length-1][1];
        }
        void UpdatePlayableBounds()
        {
            if(boundsTime==Time)return;boundsTime=Time;
            if(customScenarioBounds!=null){Array.Copy(customScenarioBounds,playableBounds,4);return;}
            if(Rules.Version!=GameVersion.OriginalReference||!Array.Exists(CityCatalog.Maps,m=>m==Scenario))
            {playableBounds[0]=0;playableBounds[1]=0;playableBounds[2]=Width;playableBounds[3]=Height;
                playableTiles[0]=0;playableTiles[1]=0;playableTiles[2]=Width-1;playableTiles[3]=Height-1;return;}
            double size=CityZoom,progress=Math.Max(0,Math.Min(1,(size-Map.Zoom[0])/(Map.Zoom[1]-Map.Zoom[0])));
            double cx=startOffsetX*(1-progress),cy=startOffsetY*(1-progress),halfWidth=size*8/9;
            // Original whole-tile bounds use ceil(min) and floor(max); RectFixed.Contains includes both edges, so the
            // last column and the top row (original maximum y) are playable. Canvas y = 14 - original y. The stored
            // bounds keep an exclusive maximum (observation semantics); the unclamped inclusive tiles feed placement.
            playableTiles[0]=25+(int)Math.Ceiling(cx-halfWidth);playableTiles[2]=25+(int)Math.Floor(cx+halfWidth);
            playableTiles[1]=14-(int)Math.Floor(cy+size/2);playableTiles[3]=14-(int)Math.Ceiling(cy-size/2);
            playableBounds[0]=Math.Max(0,playableTiles[0]);
            playableBounds[2]=Math.Min(Width,playableTiles[2]+1);
            playableBounds[1]=Math.Max(0,playableTiles[1]);
            playableBounds[3]=Math.Min(Height,playableTiles[3]+1);
        }
        // Inclusive, unclamped canvas tile bounds of the original playable area (OriginalReference cities only).
        readonly int[] playableTiles=new int[4];
        public bool IsPlayable(Cell c)
        {
            if(!InBounds(c))return false;UpdatePlayableBounds();
            return c.X>=playableBounds[0]&&c.X<playableBounds[2]&&c.Y>=playableBounds[1]&&c.Y<playableBounds[3];
        }
    }
}
