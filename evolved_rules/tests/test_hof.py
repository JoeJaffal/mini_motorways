"""gp-3.3 hall of fame (plans/2026-11-03-gp33-hall-of-fame.md): ranking, history, elites, files and resume."""
from __future__ import annotations

import json
import math

import pytest

from evolved_rules import evolve as evo
from evolved_rules import gp
from evolved_rules.evolve import Config, read_checkpoint, read_jsonl
from evolved_rules.tests.test_evolve import _h, det, fake, run, small  # noqa: F401 (fake is a fixture)

REF = gp.SEPARATED_TEXT


def hall(**kw) -> Config:
    return small(**{"hof": 3, "reference_text": REF, **kw})


def game(trips: int) -> dict:
    return {"trips": trips, "seconds": 300.0 + trips, "commands": 10 + trips}


# --- scoring and ranking -------------------------------------------------------------------------------------

def test_hof_score_is_the_mean_minus_its_standard_error():
    assert evo.hof_score({1: 10.0, 2: 10.0}, 1.0) == (10.0, 10.0)
    mean, lcb = evo.hof_score({1: 0.0, 2: 20.0}, 1.0)  # sd 14.14, se 10
    assert mean == 10.0 and lcb == pytest.approx(0.0)
    assert evo.hof_score({1: 0.0, 2: 20.0}, 2.0)[1] == pytest.approx(-10.0)
    assert evo.hof_score({1: 7.0}, 1.0) == (7.0, -math.inf)  # one seed: no error estimate


def test_update_hof_ranks_by_lower_bound_drops_copies_and_caps():
    seeds = [1, 2, 3, 4]
    games = {"ref": [game(100)] * 4,
             "steady": [game(105)] * 4,  # +5 on every seed: bound +5
             "copy": [game(105)] * 4,  # the same games as steady: counts once
             "swingy": [game(t) for t in (180, 60, 180, 60)]}  # mean +20, se 34.6: bound -14.6
    sizes = {"ref": 10, "steady": 12, "copy": 9, "swingy": 5}
    cfg = Config(hof=3)
    hall_, rows, archive = evo.update_hof(cfg, [], ["swingy", "steady", "copy"], games, "ref", seeds, sizes, gen=0)
    assert [m["text"] for m in hall_] == ["steady", "ref", "swingy"]  # the copy comes after steady: dropped
    assert rows[0]["mean_diff"] == 5.0 and rows[0]["lcb"] == 5.0 and rows[0]["seeds"] == 4
    assert rows[1]["mean_diff"] == 0.0 and rows[1]["lcb"] == 0.0
    assert rows[2]["lcb"] == pytest.approx(20.0 - math.sqrt(4800.0) / 2.0)
    assert not any(r["tested"] for r in rows) and archive == {}  # no members yet; the copy had no record
    two, _, archive = evo.update_hof(Config(hof=2), [], ["swingy", "steady"], games, "ref", seeds, sizes, gen=0)
    assert [m["text"] for m in two] == ["steady", "ref"] and list(archive) == ["swingy"]


def test_a_lucky_copy_cannot_replace_a_member_with_a_long_record():
    """Review finding: a smaller copy that plays a member's games in a lucky generation must not take its place
    with a short record (the member's long, modest record would be lost)."""
    history = {s: (1.0 if s % 2 else 3.0) for s in range(100, 140)}  # 40 seeds, mean +2, bound about +1.8
    games = {"ref": [game(100)] * 4, "m": [game(130)] * 4, "copy": [game(130)] * 4}  # +30 on all four
    hall_, rows, archive = evo.update_hof(Config(hof=3), [{"text": "m", "diffs": history, "gen": 0}], ["copy"],
                                         games, "ref", [1, 2, 3, 4], {"ref": 9, "m": 20, "copy": 3}, gen=5)
    assert [m["text"] for m in hall_] == ["m", "ref"] and rows[0]["seeds"] == 44 and rows[0]["tested"]
    assert "copy" not in archive


def test_member_copies_keep_the_longer_record_and_archive_the_other():
    games = {"ref": [game(100)] * 2, "long": [game(105)] * 2, "short": [game(105)] * 2}
    hof = [{"text": "short", "diffs": {7: 5.0}, "gen": 2}, {"text": "long", "diffs": {8: 5.0, 9: 5.0}, "gen": 1}]
    hall_, _, archive = evo.update_hof(Config(hof=3), hof, [], games, "ref", [1, 2],
                                       {"ref": 1, "long": 1, "short": 1}, gen=3)
    assert [m["text"] for m in hall_] == ["long", "ref"]
    assert archive == {"short": {"diffs": {7: 5.0, 1: 5.0, 2: 5.0}, "gen": 2}}


def test_a_text_that_comes_back_keeps_its_archived_record():
    games = {"ref": [game(100)] * 2, "back": [game(90), game(110)]}
    archive = {"back": {"diffs": {5: 4.0, 6: 6.0}, "gen": 1}}
    hall_, rows, archive = evo.update_hof(Config(hof=2), [], ["back"], games, "ref", [1, 2],
                                         {"ref": 1, "back": 1}, gen=4, archive=archive)
    back = next(m for m in hall_ if m["text"] == "back")
    assert back["diffs"] == {5: 4.0, 6: 6.0, 1: -10.0, 2: 10.0} and back["gen"] == 1 and archive == {}
    assert not next(r for r in rows if r["hash"] == evo.text_hash("back"))["tested"]  # back, but on probation


def test_members_keep_their_history_and_a_lucky_newcomer_falls_back():
    sizes = {"ref": 10, "member": 10, "lucky": 10}
    cfg = Config(hof=2)
    gen0 = {"ref": [game(100)] * 4, "member": [game(t) for t in (104, 106, 104, 106)]}
    hall_, _, archive = evo.update_hof(cfg, [{"text": "member", "diffs": {}, "gen": 0}], [], gen0, "ref",
                                       [1, 2, 3, 4], sizes, gen=0)
    assert [m["text"] for m in hall_] == ["member", "ref"]
    # generation 1: a newcomer is far ahead on its first four seeds and takes the top
    gen1 = {"ref": [game(100)] * 4, "member": [game(t) for t in (104, 106, 104, 106)],
            "lucky": [game(t) for t in (140, 150, 140, 150)]}
    hall_, rows, archive = evo.update_hof(cfg, hall_, ["lucky"], gen1, "ref", [5, 6, 7, 8], sizes, gen=1,
                                         archive=archive)
    assert [m["text"] for m in hall_] == ["lucky", "member"] and [r["tested"] for r in rows] == [False, True]
    assert sorted(hall_[1]["diffs"]) == [1, 2, 3, 4, 5, 6, 7, 8] and hall_[0]["gen"] == 1 and hall_[1]["gen"] == 0
    assert list(archive) == ["ref"]
    # generation 2: re-tested on new seeds it loses badly and drops below the steady member
    gen2 = {"ref": [game(100)] * 4, "member": [game(t) for t in (104, 106, 104, 106)],
            "lucky": [game(t) for t in (40, 60, 40, 60)]}
    hall_, rows, archive = evo.update_hof(cfg, hall_, [], gen2, "ref", [9, 10, 11, 12], sizes, gen=2,
                                         archive=archive)
    assert [m["text"] for m in hall_] == ["member", "ref"] and list(archive) == ["lucky"]
    assert rows[0]["seeds"] == 12 and rows[1]["seeds"] == 12  # the reference came back with its 8-seed record


def test_a_seed_drawn_again_is_counted_once():
    cfg = Config(hof=2)
    games = {"ref": [game(100)] * 2, "m": [game(110), game(90)]}
    hall_, _, _ = evo.update_hof(cfg, [{"text": "m", "diffs": {1: 10.0, 2: -10.0}, "gen": 0}], [], games, "ref",
                                 [1, 2], {"m": 3, "ref": 3}, gen=1)
    assert next(m for m in hall_ if m["text"] == "m")["diffs"] == {1: 10.0, 2: -10.0}


def test_a_newcomer_skips_the_first_round_seeds_it_was_picked_on():
    cfg = Config(hof=3)
    games = {"ref": [game(100)] * 4, "member": [game(110)] * 4,
             "new": [game(200), game(200), game(90), game(110)]}  # picked for its first two seeds
    hall_, rows, _ = evo.update_hof(cfg, [{"text": "member", "diffs": {}, "gen": 0}], ["new"], games, "ref",
                                    [1, 2, 3, 4], {"ref": 3, "member": 3, "new": 3}, gen=1, skip_new=2)
    by = {m["text"]: m["diffs"] for m in hall_}
    assert by["new"] == {3: -10.0, 4: 10.0}  # not +100 on seeds 1 and 2
    assert sorted(by["member"]) == [1, 2, 3, 4] and sorted(by["ref"]) == [3, 4]
    assert [m["text"] for m in hall_] == ["member", "ref", "new"]


# --- config ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kw, msg", [
    (dict(hof=3), "needs a reference_text"),
    (dict(hof=0, reference_text=REF), "only used with hof"),
    (dict(hof=1, reference_text=REF), "at least elites"),
    (dict(hof=3, reference_text=REF, hof_se=-1.0), "hof_se"),
    (dict(hof=3, reference_text=REF, hof_se=math.inf), "hof_se"),
    (dict(hof=3, reference_text="priority: nonsense_term"), "bad reference text"),
    (dict(hof=3, reference_text=gp.with_remove(REF)), "4-tree reference text needs remove_tree"),
])
def test_bad_hall_settings_are_refused(kw, msg):
    with pytest.raises(ValueError, match=msg):
        small(**kw).check()


def test_cli_needs_a_reference_with_hof(capsys):
    with pytest.raises(SystemExit) as e:
        evo.main(["--run", "x", "--hof", "3"])
    assert e.value.code == 2 and "reference" in capsys.readouterr().err


def test_cli_reads_the_reference_file(fake, tmp_path, monkeypatch):
    ref = tmp_path / "ref.txt"
    ref.write_text(REF + "\n", encoding="utf-8")
    seen = {}

    def fake_open(cfg, run_dir, resume=False, overrides=None):
        seen["cfg"] = cfg
        raise evo.RunExistsError("stop here")

    monkeypatch.setattr(evo, "open_run", fake_open)
    assert evo.main(["--run", "x", "--hof", "4", "--reference", str(ref), "--hof-se", "0.5"]) == 2
    assert seen["cfg"].hof == 4 and seen["cfg"].reference_text == REF and seen["cfg"].hof_se == 0.5


# --- the loop --------------------------------------------------------------------------------------------------

def test_hof_off_writes_format_3_and_no_hall(fake, tmp_path):
    run(tmp_path, "a", small(min_gens=50, max_gens=2))
    state = read_checkpoint(tmp_path / "a")
    assert state["format"] == evo.CHECKPOINT_FORMAT and "hof" not in state
    assert all("hof" not in r for r in read_jsonl(tmp_path / "a" / evo.GENERATIONS))


def test_a_hall_run_records_the_hall_and_takes_elites_and_validation_from_it(fake, tmp_path):
    cfg = hall(min_gens=50, max_gens=4, validate_top=2)
    run(tmp_path, "a", cfg)
    state = read_checkpoint(tmp_path / "a")
    assert state["format"] == evo.HOF_CHECKPOINT_FORMAT and 1 <= len(state["hof"]) <= cfg.hof
    recs = read_jsonl(tmp_path / "a" / evo.GENERATIONS)
    ref = evo.canonical(cfg, REF)
    per_gen = cfg.n_s4 + cfg.n_s8
    turnovers = 0
    for r in recs:
        hashes = [h["hash"] for h in r["hof"]]
        tested = [h["hash"] for h in r["hof"] if h["tested"]]
        assert len(hashes) >= cfg.elites
        assert r["elites"] == list(dict.fromkeys(tested + hashes))[:cfg.elites]  # probation: re-tested first
        # validation: the re-tested members, or the hall's top when newcomers took every place
        assert [v["hash"] for v in r["validated_all"]] == (tested or hashes)[:cfg.validate_top]
        turnovers += not tested
        assert all(1 <= h["seeds"] <= per_gen * (r["gen"] + 1) for h in r["hof"])
        lcbs = [(h["lcb"], h["mean_diff"]) for h in r["hof"]]
        assert lcbs == sorted(lcbs, reverse=True)
        assert "reference_trips" in r
    assert turnovers < len(recs)  # the probation case is exercised too
    for m in state["hof"]:
        if m["text"] == ref:
            assert set(m["diffs"].values()) == {0.0}  # the reference against itself
    # the next population starts with the last generation's elites unchanged
    assert [evo.text_hash(t) for t in state["population"][:cfg.elites]] == recs[-1]["elites"]


def test_generation_0_hall_holds_the_reference_and_the_seeds(fake, tmp_path):
    seed = gp.HAND_TEXT
    cfg = hall(min_gens=50, max_gens=1, seed_texts=(seed,))
    state = evo.start(cfg, tmp_path / "a")
    assert [m["text"] for m in state["hof"]] == [evo.canonical(cfg, REF), evo.canonical(cfg, seed)]
    assert all(m["diffs"] == {} for m in state["hof"])


def test_a_steady_rule_survives_lucky_swingy_rivals_only_with_the_hall(fake, tmp_path):
    """gp-3.2's failure in miniature: one steady rule (the reference) against rules that swing +120 / -130 by
    seed. Without the hall the racing top is the luckiest rivals and the steady rule is lost; with it the steady
    rule keeps bound 0 against the rivals' mostly negative bounds and stays an elite every generation."""
    base = dict(pop=12, racing_top=3, elites=2, n_s4=2, n_s8=6, min_gens=50, max_gens=5, validate_top=1)
    steady = evo.canonical(hall(**base), REF)

    def swingy(text, seed, cap_s):
        trips = 200 if text == steady else (320 if _h(f"{text}|{seed}") % 2 else 70)
        return {"trips": trips, "seconds": 300.0 + trips, "commands": 10 + trips, "tiles_built": 5,
                "trips_per_tile": 0.0, "scenario_seed": seed}

    fake["game"] = swingy
    run(tmp_path, "off", small(**base))
    off = read_jsonl(tmp_path / "off" / evo.GENERATIONS)
    assert any(evo.text_hash(steady) not in r["elites"] for r in off)  # precondition: the plain loop loses it
    run(tmp_path, "on", hall(**base))
    on = read_jsonl(tmp_path / "on" / evo.GENERATIONS)
    assert all(evo.text_hash(steady) in r["elites"] for r in on)


def test_resume_of_a_hall_run_matches_an_uninterrupted_run(fake, tmp_path, monkeypatch):
    cfg = hall(min_gens=50, max_gens=4)
    run(tmp_path, "full", cfg)
    real = evo.write_checkpoint
    calls = {"n": 0}

    def dying(run_dir, state):
        calls["n"] += 1
        if calls["n"] == 3:  # start, gen 0, then die before gen 1's checkpoint
            raise KeyboardInterrupt
        real(run_dir, state)

    monkeypatch.setattr(evo, "write_checkpoint", dying)
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, "kill", cfg)
    monkeypatch.setattr(evo, "write_checkpoint", real)
    run(tmp_path, "kill", resume=True)
    full, kill = (read_jsonl(tmp_path / n / evo.GENERATIONS) for n in ("full", "kill"))
    assert det(kill) == det(full) and [r["hof"] for r in kill] == [r["hof"] for r in full]
    a, b = read_checkpoint(tmp_path / "full"), read_checkpoint(tmp_path / "kill")
    for key in ("generation", "population", "rng", "convergence", "validated", "hof", "hof_archive"):
        assert a[key] == b[key]


def test_differences_match_the_games_with_a_reference_outside_the_population(fake, tmp_path):
    from evolved_rules.tests.test_evolve import synthetic
    cfg = hall(min_gens=50, max_gens=3, reference_text=gp.CLEAN_TEXT)
    ref = evo.canonical(cfg, gp.CLEAN_TEXT)
    run(tmp_path, "a", cfg)
    state = read_checkpoint(tmp_path / "a")
    assert ref not in evo.initial_population(cfg)
    checked = 0
    records = [(m["text"], m["diffs"]) for m in state["hof"]]
    records += [(t, v["diffs"]) for t, v in state["hof_archive"].items()]
    for text, diffs in records:
        for s, d in diffs.items():
            assert d == synthetic(text, s, cfg.cap_s)["trips"] - synthetic(ref, s, cfg.cap_s)["trips"]
            checked += 1
    assert checked > 20


def test_validation_games_never_change_the_hall(fake, tmp_path):
    """Requirement: the validation seeds decide the incumbent only. Two runs whose games differ only on the
    validation seeds must keep the same hall, archive, elites and populations."""
    from evolved_rules.tests.test_evolve import synthetic
    cfg = hall(min_gens=50, max_gens=4)
    run(tmp_path, "a", cfg)

    def skewed(text, seed, cap_s):
        g = synthetic(text, seed, cap_s)
        if seed in cfg.validation:
            g = {**g, "trips": g["trips"] + (500 if _h(text) % 2 else -50)}
        return g

    fake["game"] = skewed
    run(tmp_path, "b", cfg)
    a, b = read_checkpoint(tmp_path / "a"), read_checkpoint(tmp_path / "b")
    for key in ("population", "rng", "hof", "hof_archive"):
        assert a[key] == b[key]
    ra, rb = (read_jsonl(tmp_path / n / evo.GENERATIONS) for n in ("a", "b"))
    assert [(r["elites"], r["hof"]) for r in ra] == [(r["elites"], r["hof"]) for r in rb]
    assert [r["validated"]["mean"] for r in ra] != [r["validated"]["mean"] for r in rb]  # it did change those


def test_hof_needs_two_extra_seeds():
    with pytest.raises(ValueError, match="at least 2 extra seeds"):
        hall(n_s8=1).check()


def test_an_old_run_resumes_with_explicit_default_hall_flags(fake, tmp_path):
    """Review finding: a run made before the hall existed has no hof fields in config.json; resuming it with
    --hof 0 or --hof-se 1 (the defaults it ran with) must be accepted."""
    run(tmp_path, "a", small(min_gens=50, max_gens=1))
    path = tmp_path / "a" / evo.CONFIG
    config = json.loads(path.read_text(encoding="utf-8"))
    for k in ("hof", "reference_text", "hof_se"):
        del config["params"][k]
    path.write_text(json.dumps(config), encoding="utf-8")
    cfg, _ = evo.load(tmp_path / "a", overrides={"hof": 0, "hof_se": 1.0, "max_gens": 2})
    assert cfg.hof == 0 and cfg.max_gens == 2
    with pytest.raises(ValueError, match="differs from the saved run"):
        evo.load(tmp_path / "a", overrides={"hof_se": 2.0})


def test_a_checkpoint_that_does_not_match_the_config_is_refused(fake, tmp_path):
    run(tmp_path, "a", hall(min_gens=50, max_gens=1))
    path = tmp_path / "a" / evo.CONFIG
    config = json.loads(path.read_text(encoding="utf-8"))
    config["params"].update(hof=0, reference_text="")
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match hof"):
        evo.load(tmp_path / "a")
