"""GP representation: primitive sets, scaled terminals, individuals as text, TreePolicy and variation (Phase 2 Task 3).

An individual is a list of three DEAP PrimitiveTrees (decision P2-5: Remove is dropped):

    priority  over candidate + global terminals   score of one route candidate (highest is built)
    hold      over global terminals               build while the best priority is at least this
    upgrade   over offer + global terminals       score of one upgrade offer (highest is taken)

Terminals are the feature dicts of features.py divided by a fixed power of two (decision P2-7). Dividing by a
power of two is exact in binary floating point, so it never changes an order or an equality: the Phase 1
rules written as trees (HAND_TEXT, SEPARATED_TEXT) play exactly the Phase 1 games. The hand rule's
`best >= 4 - road_stock` becomes `-tiles/64 >= 0.0625 - stock/64`, the same comparison scaled by 1/64.

Everything DEAP must find again in a spawned Windows worker or when unpickling a checkpoint lives at module
level: the creator classes, the primitive sets, the primitives and the ephemeral-constant generator. The text
form of an individual (`individual_text`) is canonical and is the cache key of the evaluation engine.
"""
from __future__ import annotations

import math
import random
import re
from collections.abc import Sequence
from functools import lru_cache

from deap import base, creator, gp

from .features import N_ITEM_TYPES

# --- terminals -----------------------------------------------------------------------------------------------
# The order is the order of the feature dicts minus DROPPED_TERMS (test_gp checks it); it fixes the compiled
# argument order.

# Feature keys that never vary in real games, so a tree that reads them wastes its structure. Measured with
# autopsy.py over the 50 validation games of gp-1's best rule (2026-11-02): pending_refunds was 0 at every one
# of the decisions (no policy removes roads, decision P2-5) and no offer ever had type 5 (the unused item slot).
# features.py still computes them; only the trees leave them out.
# pending_refunds was dropped for gp-2 and is back for gp-3, where removals make it vary (a pending tile waits for
# its committed cars); in a game without removals it is 0, so a gp-1 text that reads it plays exactly as before.
DROPPED_TERMS = frozenset({"type_5"})


def _keep(*names: str) -> tuple[str, ...]:
    return tuple(n for n in names if n not in DROPPED_TERMS)


CANDIDATE_TERMS = _keep(
    "tiles_needed", "bridges_needed", "path_len", "turns", "new_junctions", "shared_cells",
    "is_attach", "is_direct", "is_separated",
    "path_cost_s", "house_served", "shop_demand", "shop_unassigned", "shop_capacity", "shop_overcrowded",
    "shop_rate", "shop_houses", "colour_margin",
    "is_clean", "near_shop_junctions", "ends_near_shop", "shop_doorstep_degree", "shop_heading", "shop_stuck",
)
GLOBAL_TERMS = _keep(
    "road_stock", "bridge_stock", "time", "unserved_houses",
    "pending_refunds", "next_offer_s", "disconnected_components", "unserved_shops", "edge_distance",
    "worst_overcrowded", "worst_margin", "shops", "houses",
    "worst_doorstep_degree", "most_stuck_near_shop", "stuck_cars",
)
OFFER_TERMS = _keep("offer_roads", "amount", *(f"type_{t}" for t in range(N_ITEM_TYPES)), "stock_of_type")

# gp-3: the remove tree scores one removal candidate (features.removal_features); see plans/2026-11-03-gp3-traffic.md
REMOVAL_TERMS = ("rm_degree", "rm_dist", "rm_links_doorstep", "rm_doorstep_degree", "rm_shop_junctions",
                 "rm_shop_heading", "rm_shop_stuck", "rm_shop_unassigned")

PRIORITY_TERMS = CANDIDATE_TERMS + GLOBAL_TERMS
HOLD_TERMS = GLOBAL_TERMS
UPGRADE_TERMS = OFFER_TERMS + GLOBAL_TERMS
REMOVE_TERMS = REMOVAL_TERMS + GLOBAL_TERMS

TILES = PINS = COUNT = 64  # tiles, stock, pins, pin rates and counts
SHORT_S = 1024  # route costs, overcrowding timers, time to the next offer
GAME_S = 4096  # game time (the cap is 3600 s)
FLAG = 1
DEGREE = 8  # links of a cell (0..8)

_ALL_SCALES: dict[str, int] = {
    # candidate
    "tiles_needed": TILES, "bridges_needed": COUNT, "path_len": TILES, "turns": COUNT, "new_junctions": COUNT,
    "shared_cells": TILES, "is_attach": FLAG, "is_direct": FLAG, "is_separated": FLAG,
    "path_cost_s": SHORT_S, "house_served": FLAG, "shop_demand": PINS, "shop_unassigned": PINS,
    "shop_capacity": PINS, "shop_overcrowded": SHORT_S, "shop_rate": PINS, "shop_houses": COUNT,
    "colour_margin": PINS,  # trips per minute, like a pin rate
    "is_clean": FLAG, "near_shop_junctions": COUNT, "ends_near_shop": FLAG, "shop_doorstep_degree": DEGREE,
    "shop_heading": COUNT, "shop_stuck": COUNT,
    # global
    "road_stock": TILES, "bridge_stock": COUNT, "time": GAME_S, "unserved_houses": COUNT,
    "pending_refunds": TILES, "next_offer_s": SHORT_S, "disconnected_components": COUNT,
    "unserved_shops": COUNT, "edge_distance": TILES, "worst_overcrowded": SHORT_S, "worst_margin": PINS,
    "shops": COUNT, "houses": COUNT,
    "worst_doorstep_degree": DEGREE, "most_stuck_near_shop": COUNT, "stuck_cars": COUNT,
    # offer
    "offer_roads": TILES, "amount": COUNT, **{f"type_{t}": FLAG for t in range(N_ITEM_TYPES)},
    "stock_of_type": COUNT,
    # removal (gp-3)
    "rm_degree": DEGREE, "rm_dist": DEGREE, "rm_links_doorstep": FLAG, "rm_doorstep_degree": DEGREE,
    "rm_shop_junctions": COUNT, "rm_shop_heading": COUNT, "rm_shop_stuck": COUNT, "rm_shop_unassigned": PINS,
}
SCALE: dict[str, int] = {k: v for k, v in _ALL_SCALES.items() if k not in DROPPED_TERMS}

# --- functions -----------------------------------------------------------------------------------------------
# Plain floats in, a float out (or inf/nan, never an exception: float * and / overflow to inf).


def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def pdiv(a, b):
    """Protected division: 1.0 when the divisor is 0 (Koza's convention)."""
    return a / b if b != 0 else 1.0


def min_(a, b):
    return a if a <= b else b


def max_(a, b):
    return a if a >= b else b


def neg(a):
    return -a


def if_gt(a, b, c, d):
    """c if a > b else d (nan compares false, so it picks d)."""
    return c if a > b else d


FUNCTIONS = ((add, 2, "add"), (sub, 2, "sub"), (mul, 2, "mul"), (pdiv, 2, "pdiv"), (min_, 2, "min"),
             (max_, 2, "max"), (neg, 1, "neg"), (if_gt, 4, "if_gt"))
FUNCTION_NAMES = tuple(name for _, _, name in FUNCTIONS)

# --- ephemeral constants -------------------------------------------------------------------------------------

CONST_CHOICES = (-1.0, -0.5, 0.25, 0.5, 1.0, 2.0, 4.0)


def ephemeral_constant() -> float:
    """Half the time one of CONST_CHOICES, else uniform(-1, 1) rounded to 2 decimals (never -0.0).

    Module level so DEAP's ephemeral class pickles by reference (a lambda cannot be pickled on Windows).
    Draws from the global `random` module, which DEAP's operators use and evolve.py seeds.
    """
    if random.random() < 0.5:
        return random.choice(CONST_CHOICES)
    return round(random.uniform(-1.0, 1.0), 2) + 0.0  # + 0.0 turns -0.0 into 0.0: one text per value


# --- primitive sets ------------------------------------------------------------------------------------------

def _make_set(name: str, terms: tuple[str, ...]) -> gp.PrimitiveSet:
    pset = gp.PrimitiveSet(name, len(terms))
    pset.renameArguments(**{f"ARG{i}": t for i, t in enumerate(terms)})
    for fn, arity, fname in FUNCTIONS:
        pset.addPrimitive(fn, arity, name=fname)
    # one ephemeral class per set (DEAP refuses one name with different functions or types across sets)
    pset.addEphemeralConstant(f"const_{name}", ephemeral_constant)
    return pset


PRIORITY_SET = _make_set("priority", PRIORITY_TERMS)
HOLD_SET = _make_set("hold", HOLD_TERMS)
UPGRADE_SET = _make_set("upgrade", UPGRADE_TERMS)
REMOVE_SET = _make_set("remove", REMOVE_TERMS)
TREE_NAMES = ("priority", "hold", "upgrade")  # a gp-1 / gp-2 individual
PSETS = (PRIORITY_SET, HOLD_SET, UPGRADE_SET)
TREE_TERMS = (PRIORITY_TERMS, HOLD_TERMS, UPGRADE_TERMS)
# gp-3 individuals have a fourth tree, remove. Every function below takes 3 or 4 trees; tree i is always
# ALL_TREE_NAMES[i] over ALL_PSETS[i].
ALL_TREE_NAMES = TREE_NAMES + ("remove",)
ALL_PSETS = PSETS + (REMOVE_SET,)
ALL_TREE_TERMS = TREE_TERMS + (REMOVE_TERMS,)
TREE_COUNTS = (3, 4)

MAX_DEPTH = 6  # static limit per tree (P2-9)
INIT_MIN_DEPTH, INIT_MAX_DEPTH = 2, 4  # ramped half-and-half for random individuals (P2-9)
MUT_MIN_DEPTH, MUT_MAX_DEPTH = 0, 2  # subtrees grown by uniform mutation

# --- creator classes (module top level: workers and checkpoints must find them) ------------------------------

if not hasattr(creator, "RulesFitness"):
    # (mean trips, mean seconds), both maximised, compared lexicographically (P2-4)
    creator.create("RulesFitness", base.Fitness, weights=(1.0, 1.0))
if not hasattr(creator, "RulesIndividual"):
    creator.create("RulesIndividual", list, fitness=creator.RulesFitness)

# --- the Phase 1 rules as trees ------------------------------------------------------------------------------
# hand:      priority = -tiles_needed,                     hold = 4 - road_stock, upgrade = offer_roads
# separated: priority = -tiles_needed + 1000 is_separated, the rest as hand
# Every term is scaled by 1/64 (the divisor of tiles_needed, road_stock and offer_roads): 4/64 = 0.0625 and
# 1000/64 = 15.625 are exact, is_separated is a flag (divisor 1).

HAND_TEXT = "priority: neg(tiles_needed)\nhold: sub(0.0625, road_stock)\nupgrade: offer_roads"
SEPARATED_TEXT = ("priority: add(neg(tiles_needed), mul(15.625, is_separated))\n"
                  "hold: sub(0.0625, road_stock)\nupgrade: offer_roads")
# clean (rules.CleanHand): + 2000 is_clean (2000/64 = 31.25); as a 3-tree text it plays CleanHand only when the
# policy is given clean routes (a 4-tree text always is)
CLEAN_TEXT = ("priority: add(add(neg(tiles_needed), mul(15.625, is_separated)), mul(31.25, is_clean))\n"
              "hold: sub(0.0625, road_stock)\nupgrade: offer_roads")
NEVER_REMOVE = "-1.0"


def with_remove(text: str, remove: str = NEVER_REMOVE) -> str:
    """A 3-tree text as a 4-tree (gp-3) text with the given remove tree (default: never remove); a 4-tree text
    is returned in canonical form, unchanged otherwise."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) == len(TREE_NAMES):
        lines.append(f"remove: {remove}")
    return individual_text(individual_from_text("\n".join(lines)))


# --- text <-> individual -------------------------------------------------------------------------------------

_TOKEN = re.compile(r"[(),]|[^\s(),]+")
_PUNCT = ("(", ")", ",")


def _skeleton(expr: str) -> list[str]:
    """The punctuation of an expression with every name and number written 'x' (whitespace dropped).

    DEAP's from_string splits on parentheses and commas and then ignores them, so '(road_stock' or
    'neg road_stock' would parse; comparing skeletons with str(tree) rejects any text not in DEAP's form.
    """
    return [t if t in _PUNCT else "x" for t in _TOKEN.findall(expr)]


def _check_tokens(expr: str, index: int) -> None:
    """Every token is a function or terminal of this tree's set, or a finite number float() accepts.

    Run before from_string, which eval()s every unknown token: '1/0' or '10**400' would otherwise raise
    ZeroDivisionError or OverflowError, and '0x10' would be read as 16.
    """
    pset = ALL_PSETS[index]
    eph = pset.mapping[f"const_{pset.name}"]
    for tok in _TOKEN.findall(expr):
        if tok in _PUNCT or (tok in pset.mapping and pset.mapping[tok] is not eph):
            continue
        try:
            v = float(tok)
        except ValueError:
            raise ValueError(f"bad {ALL_TREE_NAMES[index]} tree {expr!r}: {tok!r} is not a name of this tree "
                             "or a number") from None
        if not math.isfinite(v):
            raise ValueError(f"bad {ALL_TREE_NAMES[index]} tree {expr!r}: {tok!r} is not a finite number")


def _zero_dropped(expr: str) -> str:
    """A dropped input (DROPPED_TERMS) written in a tree becomes the constant 0.0, the value it always has.

    So texts from before the drop (gp-1, whose best rule reads pending_refunds) still load and play exactly as
    they did; their canonical text then shows 0.0 in that place.
    """
    return re.sub(r"[^\s(),]+", lambda m: "0.0" if m.group(0) in DROPPED_TERMS else m.group(0), expr)


def _parse_tree(expr: str, index: int) -> gp.PrimitiveTree:
    """One tree from its expression; constants become this set's ephemerals (so mutEphemeral can tune them).

    The ephemeral node is built without calling its generator, so parsing never draws from `random`.
    ValueError for an unknown name, a non-numeric or non-finite constant, a wrong arity, an incomplete
    expression, extra nodes after a complete one, or parentheses and commas out of place.
    """
    pset = ALL_PSETS[index]
    name = ALL_TREE_NAMES[index]
    expr = _zero_dropped(expr)
    _check_tokens(expr, index)
    try:
        tree = gp.PrimitiveTree.from_string(expr, pset)
    except (TypeError, SyntaxError, IndexError, ValueError, ArithmeticError) as e:
        raise ValueError(f"bad {name} tree {expr!r}: {e}") from None
    eph = pset.mapping[f"const_{pset.name}"]
    for i, node in enumerate(tree):
        if isinstance(node, gp.Primitive) or (isinstance(node.value, str) and pset.mapping.get(node.value) is node):
            continue  # a function or a terminal of this set (renamed arguments keep name ARGi; value is the name)
        const = object.__new__(eph)
        const.value = float(node.value) + 0.0  # + 0.0 turns -0.0 into 0.0: one text per value
        tree[i] = const
    # from_string accepts a prefix of a valid expression, or one followed by more nodes, silently: in prefix
    # order the open argument slots (`need`) must stay positive until the last node closes the last one
    need = 1
    for node in tree:
        if need == 0:
            raise ValueError(f"bad {name} tree {expr!r}: extra nodes after a complete expression")
        need += node.arity - 1
    if need != 0:
        raise ValueError(f"bad {name} tree {expr!r}: incomplete expression (missing arguments)")
    if _skeleton(expr) != _skeleton(str(tree)):
        raise ValueError(f"bad {name} tree {expr!r}: parentheses or commas out of place (expected {tree})")
    return tree


def individual_text(ind: Sequence[gp.PrimitiveTree]) -> str:
    """Canonical text, one line per tree: 'priority: ...\\nhold: ...\\nupgrade: ...[\\nremove: ...]' (the cache
    key). 3 trees (gp-1, gp-2) or 4 (gp-3)."""
    if len(ind) not in TREE_COUNTS:
        raise ValueError(f"an individual has 3 or 4 trees, got {len(ind)}")
    return "\n".join(f"{name}: {tree}" for name, tree in zip(ALL_TREE_NAMES, ind))


def individual_from_text(text: str) -> creator.RulesIndividual:
    """Inverse of individual_text (fitness invalid). Blank lines and surrounding whitespace are ignored."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) not in TREE_COUNTS:
        raise ValueError(f"expected 3 or 4 lines ({', '.join(ALL_TREE_NAMES)}), got {len(lines)}")
    trees = []
    for i, (line, name) in enumerate(zip(lines, ALL_TREE_NAMES)):
        label, sep, expr = line.partition(":")
        if not sep or label.strip() != name:
            raise ValueError(f"line {i + 1} must start with '{name}:', got {line!r}")
        trees.append(_parse_tree(expr.strip(), i))
    return creator.RulesIndividual(trees)


def _tree_exprs(texts: str | Sequence[str]) -> tuple[str, ...]:
    """An individual text, or three or four bare tree expressions -> canonical expressions."""
    if isinstance(texts, str):
        ind = individual_from_text(texts)
    else:
        texts = list(texts)
        if len(texts) not in TREE_COUNTS:
            raise ValueError(f"expected 3 or 4 tree expressions, got {len(texts)}")
        ind = [_parse_tree(t, i) for i, t in enumerate(texts)]
    return tuple(str(t) for t in ind)


def size(ind: Sequence[gp.PrimitiveTree]) -> int:
    """Total nodes over the trees (parsimony; len(ind) is the number of trees, 3 or 4)."""
    return sum(len(t) for t in ind)


def random_individual(min_depth: int = INIT_MIN_DEPTH, max_depth: int = INIT_MAX_DEPTH,
                      trees: int = 3) -> creator.RulesIndividual:
    """`trees` (3, or 4 for gp-3) ramped half-and-half trees (P2-9), drawn from the global `random` module."""
    if trees not in TREE_COUNTS:
        raise ValueError(f"an individual has 3 or 4 trees, got {trees}")
    return creator.RulesIndividual(
        gp.PrimitiveTree(gp.genHalfAndHalf(pset, min_depth, max_depth)) for pset in ALL_PSETS[:trees])


# --- the policy ----------------------------------------------------------------------------------------------

@lru_cache(maxsize=8192)
def _compile(index: int, expr: str):
    """The tree's lambda, taking the tree's terminals positionally (cached per process)."""
    return gp.compile(expr, ALL_PSETS[index])


def _scaled_reader(terms: tuple[str, ...]):
    pairs = tuple((t, float(SCALE[t])) for t in terms)
    return lambda f: [f[t] / d for t, d in pairs]


_READERS = tuple(_scaled_reader(terms) for terms in ALL_TREE_TERMS)


def _call(fn, args) -> float:
    try:
        return float(fn(*args))
    except (OverflowError, ZeroDivisionError, ValueError):
        return math.nan


def _never_positive(expr: str) -> bool:
    """True if a tree expression is a single constant <= 0 (its score can never be above 0)."""
    try:
        return float(expr) <= 0
    except ValueError:
        return False


class TreePolicy:
    """A Policy evaluating an individual's trees on scaled terminals.

    wants_globals tells agent.decide to merge the global features into every candidate and offer dict (the
    priority and upgrade trees read global terminals). coverage (default True) turns on the coverage targets
    of decision P2-6; coverage=False keeps the Phase 1 targets (HAND_TEXT then plays exactly HandRule).
    Non-finite priority and upgrade scores become -inf; a non-finite hold is returned as is (decide() never
    builds on it).

    A 3-tree text (gp-1, gp-2) has no remove tree: remove is always -1 and `removes` is False, and clean routes
    are off unless clean_routes=True, so it plays exactly as it did. A 4-tree text (gp-3) removes when its remove
    tree scores a removal candidate above 0 (a non-finite score never removes), and clean routes default to on.
    """

    wants_globals = True

    def __init__(self, texts: str | Sequence[str], coverage: bool = True, name: str = "tree",
                 clean_routes: bool | None = None) -> None:
        exprs = _tree_exprs(texts)
        self.text = "\n".join(f"{n}: {e}" for n, e in zip(ALL_TREE_NAMES, exprs))
        self.trees = len(exprs)
        self.coverage = bool(coverage)
        # a remove tree that is one constant <= 0 can never remove: skip the removal step (and its cost) then
        self.removes = self.trees == 4 and not _never_positive(exprs[3])
        # gp-3: also offer clean routes; default on for a 4-tree text, off (plays exactly as before) for 3 trees
        self.clean_routes = (self.trees == 4) if clean_routes is None else bool(clean_routes)
        self.name = name
        self._fns = tuple(_compile(i, e) for i, e in enumerate(exprs))

    def priority(self, f: dict[str, float]) -> float:
        x = _call(self._fns[0], _READERS[0](f))
        return x if math.isfinite(x) else -math.inf

    def hold(self, g: dict[str, float]) -> float:
        return _call(self._fns[1], _READERS[1](g))

    def upgrade(self, f: dict[str, float]) -> float:
        x = _call(self._fns[2], _READERS[2](f))
        return x if math.isfinite(x) else -math.inf

    def remove(self, f: dict[str, float]) -> float:
        if self.trees < 4:
            return -1.0
        x = _call(self._fns[3], _READERS[3](f))
        return x if math.isfinite(x) else -math.inf


# --- variation -----------------------------------------------------------------------------------------------

def _invalidate(ind) -> None:
    if hasattr(ind, "fitness"):
        del ind.fitness.values


def limit_depth(child, parent) -> None:
    """Static depth limit per tree: a tree taller than MAX_DEPTH is replaced by a copy of the parent's."""
    for i, tree in enumerate(child):
        if tree.height > MAX_DEPTH:
            child[i] = gp.PrimitiveTree(parent[i])


def mate(a, b):
    """One-point crossover on one tree index, in place; fitnesses invalidated.

    The index is drawn uniformly among those where both trees have at least 2 nodes: DEAP's cxOnePoint does
    nothing when either tree is a single node (HAND_TEXT's upgrade tree is), and drawing such an index would
    only make a clone. When no index qualifies the individuals are left as they are.
    """
    eligible = [i for i in range(min(len(a), len(b))) if len(a[i]) > 1 and len(b[i]) > 1]
    if eligible:
        i = random.choice(eligible)
        old_a, old_b = gp.PrimitiveTree(a[i]), gp.PrimitiveTree(b[i])
        gp.cxOnePoint(a[i], b[i])
        for child, old in ((a, old_a), (b, old_b)):
            if child[i].height > MAX_DEPTH:
                child[i] = old
    _invalidate(a)
    _invalidate(b)
    return a, b


MUTATIONS = ("uniform", "node", "ephemeral")


def _subtree(pset, type_):
    """The subtree grown by uniform mutation (full method, depth MUT_MIN_DEPTH..MUT_MAX_DEPTH)."""
    return gp.genFull(pset, MUT_MIN_DEPTH, MUT_MAX_DEPTH, type_)


def mutate(ind):
    """One tree (drawn uniformly): uniform subtree, node replacement or ephemeral mutation (drawn uniformly).

    An ephemeral mutation on a tree without constants falls back to node replacement, and node replacement
    on a one-node tree falls back to uniform (DEAP's mutNodeReplacement never touches the root, so it does
    nothing there), so the draw is not wasted. In place; a tree over MAX_DEPTH reverts; the fitness is
    invalidated. Returns (ind,) like DEAP.
    """
    i = random.randrange(len(ind))
    pset = ALL_PSETS[i]
    old = gp.PrimitiveTree(ind[i])
    kind = random.choice(MUTATIONS)
    tree = ind[i]
    if kind == "ephemeral" and not any(isinstance(type(n), gp.MetaEphemeral) for n in tree):
        kind = "node"
    if kind == "node" and len(tree) < 2:
        kind = "uniform"
    if kind == "uniform":
        gp.mutUniform(tree, expr=_subtree, pset=pset)
    elif kind == "node":
        gp.mutNodeReplacement(tree, pset=pset)
    else:
        gp.mutEphemeral(tree, "one")
    if tree.height > MAX_DEPTH:
        ind[i] = old
    _invalidate(ind)
    return (ind,)


__all__ = [
    "DROPPED_TERMS", "CANDIDATE_TERMS", "GLOBAL_TERMS", "OFFER_TERMS", "PRIORITY_TERMS", "HOLD_TERMS",
    "UPGRADE_TERMS", "SCALE",
    "FUNCTION_NAMES", "CONST_CHOICES", "ephemeral_constant", "PRIORITY_SET", "HOLD_SET", "UPGRADE_SET",
    "PSETS", "TREE_NAMES", "ALL_PSETS", "ALL_TREE_NAMES", "ALL_TREE_TERMS", "REMOVAL_TERMS", "REMOVE_TERMS",
    "REMOVE_SET", "TREE_COUNTS", "CLEAN_TEXT", "NEVER_REMOVE", "with_remove",
    "MAX_DEPTH", "HAND_TEXT", "SEPARATED_TEXT", "individual_text",
    "individual_from_text", "random_individual", "size", "TreePolicy", "mate", "mutate", "limit_depth",
]
