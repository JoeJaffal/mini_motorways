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
}
