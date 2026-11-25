using System.Collections.Generic;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        readonly HashSet<Cell> nativeJoinCells=new HashSet<Cell>();
        int nativeJoinVersion=-1;
        bool NativeJoinAt(Cell cell)
        {
            if(Rules.Version!=GameVersion.OriginalReference)return false;
            if(nativeJoinVersion!=NetworkVersion)
            {
                nativeJoinCells.Clear();var seen=new HashSet<Cell>();var accesses=new HashSet<Cell>();
                foreach(var building in Buildings)foreach(var access in Accesses(building))
                {
                    if(!accesses.Add(access))continue;
                    var end=access+Directions[AccessDirection(building,access)];
                    if(!seen.Add(end))nativeJoinCells.Add(end);
                }
                nativeJoinVersion=NetworkVersion;
            }
            return nativeJoinCells.Contains(cell);
        }
        void AttachNativeDrivewaysAt(Cell cell)
        {
            nativeJoinVersion=-1;
            if(!CanTraverse(cell))return;
            foreach(var building in Buildings)foreach(var access in Accesses(building))
                if(access+Directions[AccessDirection(building,access)]==cell)Link(access,cell);
        }
    }
}
