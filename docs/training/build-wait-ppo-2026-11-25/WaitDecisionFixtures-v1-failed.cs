using System;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Initial-state fixtures only. No actions or reference route supplied to the learner.
        void LoadWaitDecisionFixture(int seed, string split, string kind)
        {
            if (kind != "match" && kind != "mismatch" && kind != "homes" && kind != "destinations")
                throw new ArgumentException("Unknown Wait decision fixture");
            Reset(seed, ScenarioKind.EmptyLab);
            CustomScenarioId = ConstructionCurriculumId;
            ConstructionExercise = "wait-decision-" + kind;
            ConstructionReference.Clear();
            var rng = new Random(seed);
            var origin = new Cell(split == "train" ? rng.Next(14, 28) : rng.Next(29, 38), rng.Next(10, 24));
            int layout = rng.Next(4), span = rng.Next(3, 6);
            int color = rng.Next(8), otherColor = (color + rng.Next(1, 8)) % 8;
            Cell AccessOffset(int orientation) => orientation == 0 ? new Cell(0,2) : orientation == 1
                ? new Cell(1,2) : orientation == 2 ? new Cell(0,0) : new Cell(0,1);
            int[] directions = {4, 0, 6, 2};
            var entry = origin + AccessOffset(layout);
            int outwardDirection = directions[layout];
            var outward = Directions[outwardDirection];
            var end = entry;
            for (int i = 0; i <= span; i++) end += outward;
            var left = kind == "homes" ? SpawnBuilding(entry, color, true, outwardDirection)
                : SpawnBuilding(origin, color, false, 0, layout);
            int facingBack = (outwardDirection + 4) % 8;
            Building right;
            if (kind == "destinations")
            {
                int farLayout = Array.IndexOf(directions, facingBack);
                var offset = AccessOffset(farLayout);
                right = SpawnBuilding(new Cell(end.X-offset.X, end.Y-offset.Y), color, false, 0, farLayout);
            }
            else right = SpawnBuilding(end, kind == "mismatch" ? otherColor : color, true, facingBack);
            if (left == null || right == null) throw new InvalidOperationException("Wait fixture placement failed");
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = span - 1;
            ConstructionEditLimit = 1000;
            LastAction = "Wait decision fixture reset";
        }
    }
}
