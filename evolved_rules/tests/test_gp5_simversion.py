"""gp-5: results are keyed on, and stamped with, the simulator version the host reports (simulatorVersion)."""
import re
import subprocess
import sys

import pytest

import evolved_rules.engine as en
import evolved_rules.host as ho
from evolved_rules.agent import GameResult
from evolved_rules.host import PRE_VERSIONING, Host, simulator_version

HAND_TEXT = "priority: 1.0\nhold: 0.0\nupgrade: 0.0"
VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.[a-z]*\d+$")  # gp-6: also "2026-11-10.f34"


def _completed(stdout: str, returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_simulator_version_reads_the_host_version_line(monkeypatch, tmp_path):
    seen = {}

    def run(argv, **kw):
        seen["argv"], seen["stdin"] = argv, kw.get("stdin")
        return _completed("2026-11-08.6\n")

    monkeypatch.setattr(ho.subprocess, "run", run)
    assert simulator_version(tmp_path / "X.dll") == "2026-11-08.6"
    assert seen["argv"] == ["dotnet", str(tmp_path / "X.dll"), "--version"]
    assert seen["stdin"] is subprocess.DEVNULL  # an old host reads stdin: it must see EOF, not hang


@pytest.mark.parametrize("stdout,code", [("", 0), ("{\"error\": \"x\"}\n", 0), ("2026-11-08.6\n", 1)])
def test_a_host_without_a_version_is_pre_versioning(monkeypatch, tmp_path, stdout, code):
    monkeypatch.setattr(ho.subprocess, "run", lambda argv, **kw: _completed(stdout, code))
    assert simulator_version(tmp_path / "X.dll") == PRE_VERSIONING


def _fake(code: str) -> Host:
    h = Host.__new__(Host)
    h._start([sys.executable, "-c", code], 5.0)
    return h


def test_host_remembers_the_version_of_its_last_reply():
    script = ("import sys, json\n"
              "sys.stdin.readline(); print(json.dumps({'simulatorVersion': '2026-11-08.6', 'ok': 1}), flush=True)\n"
              "sys.stdin.readline(); print(json.dumps({'ok': 2}), flush=True)\n"
              "sys.stdin.readline()\n")
    h = _fake(script)
    try:
        assert h.simulator_version is None  # nothing heard yet
        h.call(command="observe")
        assert h.simulator_version == "2026-11-08.6"
        h.call(command="observe")
        assert h.simulator_version == PRE_VERSIONING  # a reply without the field
    finally:
        h.close()


def test_game_result_summary_carries_the_simulator_version():
    assert "simulator_version" in GameResult.__dataclass_fields__


def test_cache_key_version_combines_code_and_simulator(monkeypatch):
    monkeypatch.setattr(en, "_simulator_version", lambda: "2026-11-08.6")
    assert en.cache_version() == f"{en.CODE_VERSION}@2026-11-08.6"
    assert en.cache_key(HAND_TEXT, 7, 3600)[0] == f"{en.CODE_VERSION}@2026-11-08.6"


def test_cache_lines_of_another_simulator_are_not_reused(monkeypatch, tmp_path):
    path = tmp_path / "cache.jsonl"
    text = en.canonical_text(HAND_TEXT)
    monkeypatch.setattr(en, "_simulator_version", lambda: "OLD")
    e = en.Engine(workers=1, cap_s=60, cache_path=path)
    e._store(en.cache_key(text, 7, 60), {"trips": 1, "simulator_version": "OLD"})
    assert en.Engine(workers=1, cap_s=60, cache_path=path).cached(text, 7) == {"trips": 1, "simulator_version": "OLD"}
    monkeypatch.setattr(en, "_simulator_version", lambda: "NEW")
    assert en.Engine(workers=1, cap_s=60, cache_path=path).cached(text, 7) is None


def test_a_game_from_another_simulator_is_an_error(monkeypatch):
    monkeypatch.setattr(en, "_simulator_version", lambda: "2026-11-08.6")
    en.check_simulator({"simulator_version": "2026-11-08.6"}, "seed 1")
    with pytest.raises(en.EngineError, match="2026-11-08.5"):
        en.check_simulator({"simulator_version": "2026-11-08.5"}, "seed 1")


@pytest.mark.host
def test_the_built_host_reports_a_version_and_games_carry_it(host):
    version = simulator_version(ho.default_host_dll())
    assert VERSION_RE.match(version), version
    host.reset(1000)
    assert host.simulator_version == version


def test_run_configs_record_the_simulator_version(monkeypatch):
    import evolved_rules.evaluate as ev
    import evolved_rules.evolve as evo
    monkeypatch.setattr(en, "_simulator_version", lambda: "2026-11-08.6")
    assert ev._config("hand", [1], 60.0, 1, False)["simulator_version"] == "2026-11-08.6"
    assert evo._run_config(evo.Config())["simulator_version"] == "2026-11-08.6"


@pytest.mark.parametrize("saved", [None, "2026-11-08.5"])
def test_a_run_from_another_simulator_cannot_be_resumed(monkeypatch, tmp_path, saved):
    import json

    import evolved_rules.evolve as evo
    monkeypatch.setattr(en, "_simulator_version", lambda: "2026-11-08.6")
    config = {"params": evo.Config().to_json()}
    if saved is not None:
        config["simulator_version"] = saved
    (tmp_path / evo.CONFIG).write_text(json.dumps(config), encoding="utf-8")
    (tmp_path / evo.CHECKPOINT).write_bytes(b"")
    before = (tmp_path / evo.CONFIG).read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="simulator"):
        evo.load(tmp_path)
    assert (tmp_path / evo.CONFIG).read_text(encoding="utf-8") == before  # refused before touching the folder
