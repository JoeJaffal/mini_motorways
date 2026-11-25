using System;
using System.Collections.Generic;

namespace MotorwaysSim
{
    public sealed partial class TrafficWorld
    {
        public const string ConstructionCurriculumId = "construction-curriculum-v1";
        public readonly List<(string Kind, Cell From, Cell To)> ConstructionReference =
            new List<(string Kind, Cell From, Cell To)>();
        public int ConstructionEditLimit { get; private set; }
        public string ConstructionExercise { get; private set; }

        public void LoadConstructionCurriculum(int seed, string split, string exercise, int? reserveDelaySeconds = null)
        {
            if (reserveDelaySeconds.HasValue && (exercise != "midgame-network-reserve" || reserveDelaySeconds < 1 || reserveDelaySeconds > 16))
                throw new ArgumentException("Reserve delay must be 1..16 seconds and only applies to reserve practice");
            if (exercise.StartsWith("traffic-", StringComparison.Ordinal))
            {
                LoadTrafficPractice(seed, split, exercise);
                return;
            }
            if (split != "train" && split != "validation")
                throw new ArgumentException("Unknown curriculum split");
            if (exercise != "adjacent" && exercise != "bend" && exercise != "driveway" &&
                exercise != "clear" && exercise != "obstacle" &&
                exercise != "route-short" && exercise != "route-long" && exercise != "route-delay" &&
                exercise != "route-gap-one" && exercise != "route-gap-two" && exercise != "route-gap-three" &&
                exercise != "route-gate-two" && exercise != "midgame-open" && exercise != "midgame-delay" &&
                exercise != "midgame-network-join" && exercise != "midgame-network-route" &&
                exercise != "midgame-network-delay" && exercise != "midgame-network-quiet" &&
                exercise != "midgame-network-reserve" && exercise != "small-city-single" && exercise != "small-city-pairs" && exercise != "small-city-offset-pairs" && exercise != "small-city-offset-single" && exercise != "small-city-offset-stock")
                throw new ArgumentException("Unknown construction exercise");
            Reset(seed, ScenarioKind.EmptyLab);
            CustomScenarioId = ConstructionCurriculumId;
            ConstructionExercise = exercise;
            ConstructionReference.Clear();
            var rng = new Random(seed);
            if (exercise == "small-city-single" || exercise == "small-city-pairs" || exercise == "small-city-offset-pairs" || exercise == "small-city-offset-single" || exercise == "small-city-offset-stock")
            {
                LoadSmallCityExercise(rng, split, exercise.EndsWith("-pairs", StringComparison.Ordinal), exercise.StartsWith("small-city-offset", StringComparison.Ordinal), exercise == "small-city-offset-stock");
                return;
            }
            if (exercise.StartsWith("midgame-", StringComparison.Ordinal))
            {
                LoadMidgameServiceExercise(rng, split, exercise == "midgame-delay" || exercise == "midgame-network-delay",
                    exercise.StartsWith("midgame-network-", StringComparison.Ordinal) ? exercise : null, reserveDelaySeconds);
                return;
            }
            if (exercise.StartsWith("route-", StringComparison.Ordinal))
            {
                LoadLimitedRouteExercise(rng, split, exercise);
                return;
            }
            int layout = rng.Next(4);
            int color = rng.Next(3);
            int side = rng.Next(2) == 0 ? -1 : 1;
            var origin = new Cell(split == "train" ? rng.Next(11, 20) : rng.Next(30, 38), rng.Next(10, 19));
            var shop = SpawnBuilding(origin, color, false, 0, layout);
            if (shop == null) throw new InvalidOperationException("Destination placement failed");
            var outward = Directions[shop.DrivewayDirection];
            var sideways = new Cell(-outward.Y, outward.X);
            var outside = shop.Access + outward;
            Cell At(int x, int y) => new Cell(outside.X + x*outward.X + y*sideways.X,
                                             outside.Y + x*outward.Y + y*sideways.Y);
            var path = new List<Cell>();
            int supply;
            int firstMissing;
            int missingCount;
            bool rotation = exercise == "driveway";
            bool empty = exercise == "clear" || exercise == "obstacle";

            if (exercise == "bend")
            {
                // Near both ends the road stubs retain different headings.
                int lateral = rng.Next(1, 3);
                path.AddRange(new[] {At(6, side*lateral), At(5, side*lateral), At(4, side*lateral),
                    At(3, side*(lateral-1)), At(2, 0), At(1, 0), At(0, 0)});
                firstMissing = 2;
                missingCount = 2 + rng.Next(2);
                supply = missingCount;
            }
            else if (exercise == "obstacle")
            {
                int distance = rng.Next(4, 8);
                int center = rng.Next(2, distance-1);
                foreach (int col in new[] {0, side})
                {
                    var blocked = At(center, col);
                    Blocked[blocked.X, blocked.Y] = true;
                    Unzoneable[blocked.X, blocked.Y] = true;
                }
                for (int x = distance; x >= 0; x--)
                    path.Add(At(x, x == center ? -side : 0));
                firstMissing = 0;
                missingCount = path.Count - 1;
                supply = distance - 1;
            }
            else if (exercise == "clear")
            {
                int distance = rng.Next(3, 8);
                int lateral = side*rng.Next(3);
                for (int x = distance; x >= 0; x--)
                {
                    path.Add(At(x, lateral));
                    lateral -= Math.Sign(lateral);
                }
                firstMissing = 0;
                missingCount = path.Count - 1;
                supply = distance - 1;
            }
            else
            {
                int distance = rng.Next(5, 8);
                bool diagonal = !rotation && rng.Next(2) == 0;
                for (int x = distance; x >= 0; x--)
                    path.Add(At(x, diagonal ? x*side : 0));
                firstMissing = rotation ? 0 : rng.Next(1, distance-2);
                missingCount = rotation ? 0 : 2;
                supply = rotation ? 0 : 2;
            }

            var home = SpawnBuilding(path[0], color, true, Direction(path[0], path[1]));
            if (home == null) throw new InvalidOperationException("House placement failed");
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = 20;
            if (!empty)
            {
                for (int i = 0; i < path.Count-1; i++)
                {
                    if (i >= firstMissing && i < firstMissing+missingCount) continue;
                    if (!DrawRoad(path[i], path[i+1]))
                        throw new InvalidOperationException("Scripted stub placement failed");
                }
            }
            if (rotation)
            {
                // Retain a working route on one quarter of layouts. Other layouts
                // have a real road spur on the wrong house side.
                if (seed % 4 == 0)
                    ConstructionReference.Add(("finish", path[0], path[0]));
                else
                {
                    int correct = Direction(path[0], path[1]);
                    int wrong = (correct + (side > 0 ? 2 : 6)) % 8;
                    var wrongSide = path[0] + Directions[wrong];
                    var spurEnd = wrongSide + outward;
                    if (!DrawRoad(wrongSide, spurEnd) || !SetHouseDriveway(home.Id, wrong))
                        throw new InvalidOperationException("Wrong driveway fixture failed");
                    ConstructionReference.Add(("rotate", path[0], path[1]));
                }
            }
            else
            {
                for (int i = empty ? 1 : firstMissing; i < firstMissing + missingCount; i++)
                    ConstructionReference.Add(("draw", path[i], path[i+1]));
            }
            Array.Clear(Inventory, 0, Inventory.Length);
            Inventory[0] = supply;
            ConstructionEditLimit = rotation ? 1 : empty ? supply + 1 : supply;
            LastAction = "Construction curriculum reset";
        }

        public bool[] ConstructionDriveways()
        {
            RequireConnectionPractice(constructionCurriculum: true);
            var mask = new bool[8];
            if (ConstructionExercise != "driveway" || Failed || ScenarioRejected) return mask;
            var home = Buildings.Find(b => b.IsHouse);
            for (int d=0; d<8; d++)
            {
                var outside = home.Cell + Directions[d];
                mask[d] = d!=home.DrivewayDirection && PracticeDriveway(home.Cell, d)
                          && !Blocked[outside.X,outside.Y];
            }
            return mask;
        }
    }
}
