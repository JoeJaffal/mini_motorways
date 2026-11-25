using System;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        Cell? routePracticeGate;
        double routePracticeGateOpens;

        void LoadLimitedRouteExercise(Random rng, string split, string exercise)
        {
            int layout = rng.Next(4), color = rng.Next(3), lateral = rng.Next(-1, 2);
            int distance = exercise == "route-short" ? rng.Next(3, 5) : rng.Next(5, 7);
            var origin = new Cell(split == "train" ? rng.Next(12, 24) : rng.Next(30, 37), rng.Next(11, 19));
            var shop = SpawnBuilding(origin, color, false, 0, layout);
            if (shop == null) throw new InvalidOperationException("Limited route destination placement failed");
            var outward = Directions[shop.DrivewayDirection];
            var sideways = new Cell(-outward.Y, outward.X);
            var outside = shop.Access + outward;
            Cell At(int forward, int side) => new Cell(outside.X + forward*outward.X + side*sideways.X,
                                                       outside.Y + forward*outward.Y + side*sideways.Y);

            var homeCell = At(distance, lateral);
            var home = SpawnBuilding(homeCell, color, true, Direction(homeCell, At(distance-1, lateral)));
            if (home == null) throw new InvalidOperationException("Limited route home placement failed");
            var a = At(-4, -4);
            var b = At(distance+3, 4);
            int left = Math.Max(0, Math.Min(a.X, b.X)), right = Math.Min(Width, Math.Max(a.X, b.X)+1);
            int top = Math.Max(0, Math.Min(a.Y, b.Y)), bottom = Math.Min(Height, Math.Max(a.Y, b.Y)+1);
            customScenarioBounds = new double[] {left, top, right, bottom};
            boundsTime = double.NaN;

            // Short genuine road stubs make both rewarding and dead-end extensions available.
            Inventory[0] = 20;
            int spurSide = lateral > 0 ? -3 : 3;
            if (!DrawRoad(At(0, spurSide), At(1, spurSide)) ||
                !DrawRoad(At(distance-1, -spurSide), At(distance, -spurSide)))
                throw new InvalidOperationException("Limited route distractor placement failed");

            bool delayed = exercise == "route-delay" || exercise == "route-gate-two";
            int missing = exercise == "route-gap-one" ? 1 : exercise == "route-gap-three" ? 3 :
                          exercise == "route-gap-two" || exercise == "route-gate-two" ? 2 : distance-1;
            int gapStart = exercise == "route-gate-two" ? 2
                : missing == distance-1 ? 1 : rng.Next(1, distance-missing+1);
            int side = lateral;
            for (int x = distance-1; x > 0; x--)
            {
                int nextSide = x == distance-1 ? 0 : side;
                var from = At(x, side);
                var to = At(x-1, nextSide);
                if (x >= gapStart && x < gapStart+missing)
                    ConstructionReference.Add(("draw", from, to));
                else if (!DrawRoad(from, to))
                    throw new InvalidOperationException("Limited route supplied section failed");
                side = nextSide;
            }
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = missing + rng.Next(2);
            ConstructionEditLimit = Inventory[0] + 2;

            if (delayed)
            {
                var gate = At(2, 0);
                for (int y = top; y < bottom; y++)
                    for (int x = left; x < right; x++)
                        if ((outward.X != 0 && x == gate.X) || (outward.Y != 0 && y == gate.Y))
                        {
                            Blocked[x,y] = true;
                            Unzoneable[x,y] = true;
                        }
                routePracticeGate = gate;
                routePracticeGateOpens = 6 + 3*rng.Next(3);
            }
            LastAction = "Limited route exercise reset";
        }

        void UpdateLimitedRouteGate()
        {
            if (!routePracticeGate.HasValue || Time < routePracticeGateOpens) return;
            var gate = routePracticeGate.Value;
            Blocked[gate.X,gate.Y] = false;
            Unzoneable[gate.X,gate.Y] = false;
            routePracticeGate = null;
            Changed();
        }
    }
}
