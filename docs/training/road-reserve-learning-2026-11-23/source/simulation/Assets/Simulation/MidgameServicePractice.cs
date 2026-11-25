using System;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        Action roadReserveSpawn;
        double roadReserveSpawnTime;

        void UpdateRoadReservePractice()
        {
            if (CustomScenarioId != ConstructionCurriculumId || roadReserveSpawn == null || Time < roadReserveSpawnTime) return;
            var spawn = roadReserveSpawn;
            roadReserveSpawn = null;
            spawn();
        }

        void LoadMidgameServiceExercise(Random rng, string split, bool delayed, string networkExercise = null)
        {
            bool reserve = networkExercise == "midgame-network-reserve";
            int layout = rng.Next(4);
            int color = rng.Next(3);
            int newColor = (color + rng.Next(1, 3)) % 3;
            int lane = (rng.Next(2) == 0 ? -1 : 1) * rng.Next(6, 8);
            int gaps = rng.Next(1, 3);
            var origin = new Cell(split == "train" ? rng.Next(15, 23) : rng.Next(26, 34), rng.Next(12, 17));
            bool network = networkExercise != null;
            if (network)
            {
                gaps = networkExercise == "midgame-network-join" ? 1 :
                       networkExercise == "midgame-network-delay" ? rng.Next(1, 4) : rng.Next(2, 5);
                if (rng.Next(3) == 0) newColor = color;
            }

            var existingShop = SpawnBuilding(origin, color, false, 0, layout);
            if (existingShop == null) throw new InvalidOperationException("Existing destination placement failed");
            var outward = Directions[existingShop.DrivewayDirection];
            var sideways = new Cell(-outward.Y, outward.X);
            var approach = existingShop.Access + outward;
            Cell At(int forward, int side) => new Cell(approach.X + forward*outward.X + side*sideways.X,
                                                       approach.Y + forward*outward.Y + side*sideways.Y);
            var existingHome = At(6, 0);
            if (SpawnBuilding(existingHome, color, true, Direction(existingHome, At(5, 0))) == null)
                throw new InvalidOperationException("Existing home placement failed");

            int sideMin = Math.Min(lane, 0)-3, sideMax = Math.Max(lane, 0)+3;
            var lower = At(-4, sideMin);
            var upper = At(8, sideMax);
            customScenarioBounds = new double[] {
                Math.Max(0, Math.Min(lower.X, upper.X)), Math.Max(0, Math.Min(lower.Y, upper.Y)),
                Math.Min(Width, Math.Max(lower.X, upper.X)+1), Math.Min(Height, Math.Max(lower.Y, upper.Y)+1)
            };
            boundsTime = double.NaN;
            Inventory[0] = 40;
            for (int x = 0; x < 5; x++)
                RequireMidgameRoad(At(x, 0), At(x+1, 0));
            if (reserve)
            {
                var secondHome = At(3, -2*Math.Sign(lane));
                var secondApproach = At(3, -Math.Sign(lane));
                if (SpawnBuilding(secondHome, color, true, Direction(secondHome, secondApproach)) == null)
                    throw new InvalidOperationException("Reserve supply placement failed");
                RequireMidgameRoad(secondApproach, At(3, 0));
            }
            int trunk = network ? 4 : 3;
            for (int y = 0; y != lane; y += Math.Sign(lane))
                RequireMidgameRoad(At(trunk, y), At(trunk, y+Math.Sign(lane)));
            if (!network) RequireMidgameRoad(At(3, lane), At(4, lane));

            while (existingShop.Served == 0 && Time < 45 && !Failed) Step();
            if (existingShop.Served == 0 || Failed)
                throw new InvalidOperationException("Existing route failed its warm-up delivery");
            // Resume at a whole second so Wait steps and the gate event have a stable cadence.
            while (TickCount % 20 != 0) Step();

            var newOrigin = new Cell(origin.X + lane*sideways.X, origin.Y + lane*sideways.Y);
            int homeOffset = network ? 6 : 5;
            var newHome = At(homeOffset, lane);
            if (reserve)
            {
                roadReserveSpawnTime = Time + rng.Next(8, 17);
                roadReserveSpawn = () => {
                    // Construction can obstruct the future parcel. No hidden
                    // repair or reward substitutes for missing native service.
                    var shop = SpawnBuilding(newOrigin, newColor, false, 0, layout);
                    if (shop != null) SpawnBuilding(newHome, newColor, true, Direction(newHome, At(homeOffset-1, lane)));
                };
            }
            else
            {
                var newShop = SpawnBuilding(newOrigin, newColor, false, 0, layout);
                if (newShop == null || SpawnBuilding(newHome, newColor, true, Direction(newHome, At(homeOffset-1, lane))) == null)
                    throw new InvalidOperationException("New matching pair placement failed");
            }

            if (network)
            {
                int outer = lane + Math.Sign(lane);
                bool detour = networkExercise == "midgame-network-route" && rng.Next(2) == 0;
                Cell Route(int distance) => At(distance, detour && distance >= 1 && distance <= 2 ? outer : lane);
                if (detour)
                {
                    var obstacle = At(1, lane);
                    Blocked[obstacle.X,obstacle.Y] = true;
                    Unzoneable[obstacle.X,obstacle.Y] = true;
                }
                for (int x = 5; x > 0; x--)
                {
                    if (x <= gaps) ConstructionReference.Add(("draw", Route(x), Route(x-1)));
                    else RequireMidgameRoad(Route(x), Route(x-1));
                }
                // Dead ends alongside the useful approaches offer ordinary legal edits.
                RequireMidgameRoad(At(4, lane), At(4, outer));
                RequireMidgameRoad(At(2, 0), At(2, -Math.Sign(lane)));
                RequireMidgameRoad(At(5, outer+Math.Sign(lane)), At(6, outer+Math.Sign(lane)));
            }
            else
            {
                for (int x = 3; x > 0; x--)
                {
                    if (x <= gaps) ConstructionReference.Add(("draw", At(x, lane), At(x-1, lane)));
                    else RequireMidgameRoad(At(x, lane), At(x-1, lane));
                }
            }
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = gaps + rng.Next(2);
            ConstructionEditLimit = Inventory[0] + 2;

            if (delayed)
            {
                var gate = At(0, lane);
                Blocked[gate.X,gate.Y] = true;
                Unzoneable[gate.X,gate.Y] = true;
                routePracticeGate = gate;
                routePracticeGateOpens = Time + 6 + 3*rng.Next(3);
            }
            if (networkExercise == "midgame-network-quiet")
            {
                Inventory[0] = 20;
                foreach (var edit in ConstructionReference) RequireMidgameRoad(edit.From, edit.To);
                ConstructionReference.Clear();
                Inventory[0] = 2;
                ConstructionEditLimit = 2;
            }
            LastAction = "New destination in a working network";
        }

        void RequireMidgameRoad(Cell start, Cell end)
        {
            if (!DrawRoad(start, end))
                throw new InvalidOperationException("Existing road placement failed");
        }
    }
}
