using System;
namespace MotorwaysSim
{
    // Middle-square Weyl sequence. The installed generator's numeric stream is
    // checked against vectors obtained by invoking the user's installed assembly.
    public sealed class ReferenceRandom
    {
        const ulong WeylIncrement=13091206342165455529UL;
        public ulong State {get;private set;}
        public ulong Weyl {get;private set;}
        public long Draws {get;private set;}
        public ReferenceRandom(ulong seed){State=seed;Weyl=seed;}
        public ulong NextWord()
        {
            unchecked
            {
                Weyl+=WeylIncrement;
                ulong mixed=State*State+Weyl;
                State=(mixed<<32)|(mixed>>32);Draws++;return State;
            }
        }
        public int NextInt()=>unchecked((int)NextWord());
        public int Next(int upper)=>upper<=0?0:(int)(unchecked((uint)NextInt())%(uint)upper);
        public long NextFractionRaw()
        {
            long signed=NextInt();long doubled=signed*2;
            return doubled<0?1-doubled:doubled;
        }
        public double NextDouble()=>NextFractionRaw()/4294967296.0;
    }
    public sealed class SimulationRandom
    {
        readonly Random custom;readonly ReferenceRandom original;
        public SimulationRandom(int seed,GameVersion version)
        {if(version==GameVersion.OriginalReference)original=new ReferenceRandom(unchecked((ulong)(long)seed));else custom=new Random(seed);}
        public int Next(int upper)=>original==null?custom.Next(upper):original.Next(upper);
        public double NextDouble()=>original==null?custom.NextDouble():original.NextDouble();
        public string Algorithm=>original==null?"System.Random":"MSWS reference stream";
        public long Draws=>original?.Draws??-1;
    }
    /// Keyed draws (simulator f35 "keyed" randomness). Each draw is a pure function of (map seed, use, keys), so a
    /// draw for one purpose never shifts the draws for another: two policies on the same seed see the same spawn
    /// field, offers and phases wherever the game state lets them. SplitMix64 finaliser over a running mix.
    public enum RandomUse {Placement=1,Suburb=2,Colour=3,DoubleLot=4,ActiveColour=5,DestinationUpgrade=6,ShopLayout=7,
        Shuffle=8,DemandPhase=9,Offer=10,OfferShuffle=11,CustomPhase=12}
    public static class KeyedRandom
    {
        static ulong Mix(ulong z){unchecked{z+=0x9E3779B97F4A7C15UL;z=(z^(z>>30))*0xBF58476D1CE4E5B9UL;z=(z^(z>>27))*0x94D049BB133111EBUL;return z^(z>>31);}}
        public static ulong Word(int seed,RandomUse use,long a,long b,long c,long d,long e)
        {
            unchecked
            {
                ulong h=Mix((ulong)(long)seed);h=Mix(h^(ulong)(long)use);h=Mix(h^(ulong)a);h=Mix(h^(ulong)b);
                h=Mix(h^(ulong)c);h=Mix(h^(ulong)d);return Mix(h^(ulong)e);
            }
        }
        /// Uniform in [0,1) with 53 bits.
        public static double Double(int seed,RandomUse use,long a=0,long b=0,long c=0,long d=0,long e=0)
            =>(Word(seed,use,a,b,c,d,e)>>11)*(1.0/9007199254740992.0);
        public static int Next(int upper,int seed,RandomUse use,long a=0,long b=0,long c=0,long d=0,long e=0)
            =>upper<=0?0:(int)(Word(seed,use,a,b,c,d,e)%(ulong)upper);
    }
}
