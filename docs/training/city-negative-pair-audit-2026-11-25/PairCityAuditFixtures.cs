using System;
namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        void LoadPairDiagnostic(int seed, string exercise)
        {
            if (exercise != "pair-match" && exercise != "pair-mismatch" &&
                exercise != "pair-homes" && exercise != "pair-destinations")
                throw new ArgumentException("Unknown pairing probe");
            Reset(seed, ScenarioKind.EmptyLab);
            CustomScenarioId = ConstructionCurriculumId;
            ConstructionExercise = "clear";
            ConstructionReference.Clear();
            var rng = new Random(seed);
            var origin = new Cell(rng.Next(30, 38), rng.Next(10, 19));
            int layout = rng.Next(4);
            int span = rng.Next(3, 6);

            Cell AccessOffset(int orientation) => orientation == 0 ? new Cell(0,2) : orientation == 1
                ? new Cell(1,2) : orientation == 2 ? new Cell(0,0) : new Cell(0,1);
            int[] directions = {4, 0, 6, 2};
            var entry = origin + AccessOffset(layout);
            int outwardDirection = directions[layout];
            var outward = Directions[outwardDirection];
            var end = entry;
            for (int i = 0; i <= span; i++) end += outward;

            var left = exercise == "pair-homes"
                ? SpawnBuilding(entry, 1, true, outwardDirection)
                : SpawnBuilding(origin, exercise == "pair-match" ? 1 : 0, false, 0, layout);
            int facingBack = (outwardDirection + 4) % 8;
            Building right;
            if (exercise == "pair-destinations")
            {
                int farLayout = Array.IndexOf(directions, facingBack);
                var offset = AccessOffset(farLayout);
                right = SpawnBuilding(new Cell(end.X-offset.X, end.Y-offset.Y), 0, false, 0, farLayout);
            }
            else
                right = SpawnBuilding(end, 1, true, facingBack);
            if (left == null || right == null)
                throw new InvalidOperationException("Pair diagnostic building placement failed");
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = span - 1;
            ConstructionEditLimit = 1000; // Audit uses ordinary city actions, no edit-count success cap.
            LastAction = "Pair diagnostic reset";
        }

    }
}
