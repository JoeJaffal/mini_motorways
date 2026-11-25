using System;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        // Empty, small native cities. No reference route or suggested actions.
        void LoadSmallCityExercise(Random rng, string split, bool secondPair, bool offset = false)
        {
            int layout = rng.Next(4), color = rng.Next(3);
            int otherColor = (color + rng.Next(1, 3)) % 3;
            int distance = offset ? rng.Next(6, 10) : rng.Next(3, 6);
            int laterDistance = offset ? rng.Next(6, 10) : rng.Next(3, 6);
            int lane = (rng.Next(2) == 0 ? -1 : 1) * rng.Next(6, 9);
            var origin = new Cell(split == "train" ? rng.Next(16, 22) : rng.Next(27, 33), rng.Next(13, 18));
            var shop = SpawnBuilding(origin, color, false, 0, layout);
            if (shop == null) throw new InvalidOperationException("Small city destination placement failed");
            var outward = Directions[shop.DrivewayDirection];
            var sideways = new Cell(-outward.Y, outward.X);
            var approach = shop.Access + outward;
            Cell At(int forward, int side) => new Cell(approach.X + forward*outward.X + side*sideways.X,
                                                       approach.Y + forward*outward.Y + side*sideways.Y);
            int lateral = offset ? -Math.Sign(lane)*rng.Next(2, 5) : 0;
            int laterLateral = offset ? -Math.Sign(lane)*rng.Next(2, 5) : 0;
            var home = At(distance, lateral);
            if (SpawnBuilding(home, color, true, Direction(home, At(distance-1, lateral-Math.Sign(lateral)))) == null)
                throw new InvalidOperationException("Small city home placement failed");
            // Bounds include legal distractions and the later parcel, without
            // exposing which parcel or second color will be selected.
            var low = At(-4, -12); var high = At(offset ? 12 : 8, 12);
            customScenarioBounds = new double[] {Math.Max(0, Math.Min(low.X, high.X)), Math.Max(0, Math.Min(low.Y, high.Y)),
                Math.Min(Width, Math.Max(low.X, high.X)+1), Math.Min(Height, Math.Max(low.Y, high.Y)+1)};
            boundsTime = double.NaN;
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = distance - 1 + (secondPair ? laterDistance - 1 : 0) + rng.Next(3);
            ConstructionEditLimit = 1000; // No task edit cap: ordinary inventory/legality decides.
            if (secondPair)
            {
                int delay = rng.Next(18, 31);
                roadReserveSpawnTime = Time + delay;
                var laterOrigin = new Cell(origin.X + lane*sideways.X, origin.Y + lane*sideways.Y);
                roadReserveSpawn = () => {
                    // Roads can obstruct native placement. Do not erase them or
                    // rescue the policy. Evaluation counts a missing pair as failure.
                    var laterShop = SpawnBuilding(laterOrigin, otherColor, false, 0, layout);
                    if (laterShop != null)
                    {
                        var laterHome = At(laterDistance, lane+laterLateral);
                        SpawnBuilding(laterHome, otherColor, true, Direction(laterHome, At(laterDistance-1, lane+laterLateral-Math.Sign(laterLateral))));
                    }
                };
            }
            LastAction = "Small city service practice";
        }
    }
}
