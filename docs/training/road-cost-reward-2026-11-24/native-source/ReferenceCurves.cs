using System;
namespace MotorwaysSim
{
    public sealed class UpgradeWeightProfile
    {
        public double NotOfferedIncrease;
        public int RelativeType;
        public double[][] RelativeCurve,Timeline;
    }
    public static class ReferenceCurves
    {
        // Unweighted Hermite keys; infinite tangents denote a constant segment.
        public static double Evaluate(double[][] keys,double time,double fallback=1)
        {
            if(keys==null||keys.Length==0)return fallback;
            if(time<=keys[0][0])return keys[0][1];
            for(int i=1;i<keys.Length;i++)
            {
                if(time>=keys[i][0])continue;
                var a=keys[i-1];var b=keys[i];
                if(double.IsInfinity(a[3])||double.IsInfinity(b[2]))return a[1];
                double dt=b[0]-a[0],t=(time-a[0])/dt,t2=t*t,t3=t2*t;
                return (2*t3-3*t2+1)*a[1]+(t3-2*t2+t)*dt*a[3]+(-2*t3+3*t2)*b[1]+(t3-t2)*dt*b[2];
            }
            return keys[keys.Length-1][1];
        }
    }
}
