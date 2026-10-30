import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

from evolved_rules import verify
from evolved_rules.candidates import route_candidates, unserved_targets
from evolved_rules.executor import execute_route
from evolved_rules.host import ROOT
from evolved_rules.session import GameSession
from evolved_rules.verify import build_verifier, verify_recording

# The brief's literal git path, split over two lines.
MOHAMMAD_BEST_GAME = ("upstream/mohammad:docs/training/evidence-2026-10-28/runs/"
                      "seed-1000-parallel-02/best-game.json")


def mohammad_best_game(tmp_path: Path) -> Path:
    p = tmp_path / "best.json"
    p.write_bytes(subprocess.check_output(["git", "show", MOHAMMAD_BEST_GAME], cwd=ROOT))  # not the process cwd
    return p


# --- end to end, against the real C# verifier (builds it on the first run, about 10-60 s) ---

@pytest.mark.host
def test_mohammad_best_game_passes(tmp_path):
    ok, out = verify_recording(mohammad_best_game(tmp_path))
    assert ok, out


@pytest.mark.host
def test_our_short_game_passes(host, tmp_path):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    execute_route(g, route_candidates(s, h, shops)[0])
    for _ in range(60):
        g.wait()
    p = tmp_path / "ours.json"; g.recorder.save(p, g.raw, "test")
    ok, out = verify_recording(p)
    assert ok, out


@pytest.mark.host
def test_tampered_game_fails(host, tmp_path):
    g = GameSession(host, 1000); g.reset(); g.wait(); g.wait()
    rec = g.recorder.recording(g.raw, "test"); rec["actions"][-1]["afterTime"] += 5
    p = tmp_path / "bad.json"; p.write_text(json.dumps(rec))
    ok, out = verify_recording(p)
    assert ok is False
    assert "diverged" in out  # rejected by the replay itself, not by a verifier that failed to run


@pytest.mark.host
def test_zero_action_recording_is_rejected(host, tmp_path):
    # AiReplaySession refuses an empty replay ("Unsupported or empty AI replay"); verify_recording just reports it.
    g = GameSession(host, 1000); g.reset()
    p = tmp_path / "empty.json"; g.recorder.save(p, g.raw, "test")
    ok, out = verify_recording(p)
    assert ok is False
    assert "empty" in out.lower()


@pytest.mark.host
def test_unparseable_recording_is_rejected_not_a_fault(tmp_path):
    p = tmp_path / "garbage.json"; p.write_text("not json")
    ok, out = verify_recording(p)
    assert ok is False and "JSON" in out


@pytest.mark.host
def test_second_build_does_not_rebuild(monkeypatch):
    dll = build_verifier()
    assert dll.is_file()
    assert (verify.VERIFIER_DIR / "commit.txt").read_text().strip() == verify.VERIFIER_COMMIT
    mtime = dll.stat().st_mtime_ns

    def no_subprocess(*args, **kwargs):
        raise AssertionError("build_verifier ran a subprocess although the DLL exists")
    monkeypatch.setattr(verify, "_run", no_subprocess)
    again = build_verifier()
    assert again == dll
    assert dll.stat().st_mtime_ns == mtime


@pytest.mark.host
def test_verify_recording_reuses_the_existing_build(tmp_path, monkeypatch):
    build_verifier()

    def boom(*args, **kwargs):
        raise AssertionError("verify_recording rebuilt the verifier")
    monkeypatch.setattr(verify, "_remove_tree", boom)
    monkeypatch.setattr(verify, "_run", boom)
    monkeypatch.setattr(verify, "_build_into", boom)
    monkeypatch.setattr(verify, "_swap_in", boom)
    ok, out = verify_recording(mohammad_best_game(tmp_path))
    assert ok, out


@pytest.mark.host
def test_missing_recording_returns_false(tmp_path):
    ok, out = verify_recording(tmp_path / "nope.json")
    assert ok is False
    assert "nope.json" in out


@pytest.mark.host
def test_relative_path_from_another_cwd(host, tmp_path, monkeypatch):
    g = GameSession(host, 1000); g.reset(); g.wait(); g.wait()
    g.recorder.save(tmp_path / "ours.json", g.raw, "test")
    elsewhere = tmp_path / "elsewhere"; elsewhere.mkdir()
    monkeypatch.chdir(tmp_path)
    ok, out = verify_recording(Path("ours.json"))
    assert ok, out


@pytest.mark.skipif(shutil.which("dotnet") is None, reason="needs dotnet")
def test_real_dotnet_failing_to_load_the_dll_is_a_fault_not_a_verdict(tmp_path, monkeypatch):
    # Finding 0: a corrupt DLL or missing runtime makes dotnet exit with a host error code, not 1.
    junk = tmp_path / "TrafficHost.dll"; junk.write_bytes(b"MZ not a real dll")
    monkeypatch.setattr(verify, "build_verifier", lambda force=False: junk)
    rec = tmp_path / "rec.json"; rec.write_text("{}")
    with pytest.raises(RuntimeError, match="exit code"):
        verify_recording(rec)


@pytest.mark.host
def test_forced_rebuild_swaps_in_a_working_verifier(host, tmp_path):
    # Runs last of the real tests and alone: a forced rebuild must not overlap a running verification.
    before = build_verifier()
    after = build_verifier(force=True)
    assert after == before and after.is_file()
    assert (verify.VERIFIER_DIR / "commit.txt").read_text().strip() == verify.VERIFIER_COMMIT
    assert [p.name for p in verify.VERIFIER_DIR.parent.iterdir() if ".tmp-" in p.name or ".old-" in p.name] == []
    g = GameSession(host, 1000); g.reset(); g.wait(); g.wait()
    p = tmp_path / "ours.json"; g.recorder.save(p, g.raw, "test")
    ok, out = verify_recording(p)  # the moved build still runs
    assert ok, out


# --- no host or dotnet needed: build_verifier's state handling, with a fake _run ---

@pytest.fixture
def fake_dir(tmp_path, monkeypatch):
    d = tmp_path / "verifier"
    monkeypatch.setattr(verify, "VERIFIER_DIR", d)
    return d


def _dll_path(d: Path) -> Path:
    return d / "simulation" / "Headless" / "bin" / "Release" / "net8.0" / "TrafficHost.dll"


def fake_build(d: Path, commit: str | None = verify.VERIFIER_COMMIT, content: str = "old dll") -> Path:
    """A finished build of `commit` in d (commit None: no stamp file)."""
    dll = _dll_path(d); dll.parent.mkdir(parents=True); dll.write_text(content)
    if commit is not None:
        (d / "commit.txt").write_text(commit + "\n")
    return dll


def debris(d: Path) -> list[str]:
    return sorted(p.name for p in d.parent.iterdir() if p.name != d.name)


class FakeRun:
    """Stands in for verify._run: `git archive` writes a tiny tar, `dotnet build` creates the DLL in its project."""

    def __init__(self, d: Path, fail_dotnet: bool = False, make_dll: bool = True):
        self.d = d
        self.fail_dotnet = fail_dotnet
        self.make_dll = make_dll
        self.calls: list[list[str]] = []
        self.old_build_present_during_dotnet: bool | None = None

    def __call__(self, argv, **kwargs):
        self.calls.append([str(a) for a in argv])
        if argv[0] == "git":
            out = Path(argv[argv.index("-o") + 1])
            src = out.parent / "payload.txt"
            src.write_text("x")
            with tarfile.open(out, "w") as t:
                t.add(src, arcname="simulation/Headless/Program.cs")
            src.unlink()
        elif argv[0] == "dotnet":
            self.old_build_present_during_dotnet = _dll_path(self.d).is_file()
            if self.fail_dotnet:
                raise RuntimeError("dotnet build failed: error CS0001")
            if self.make_dll:
                dll = Path(argv[2]) / "bin" / "Release" / "net8.0" / "TrafficHost.dll"
                dll.parent.mkdir(parents=True); dll.write_text("new dll")
        return ""


def install(fake_dir, monkeypatch, **kwargs) -> FakeRun:
    fake = FakeRun(fake_dir, **kwargs); monkeypatch.setattr(verify, "_run", fake)
    return fake


def test_finished_build_is_returned_without_running_anything(fake_dir, monkeypatch):
    dll = fake_build(fake_dir); fake = install(fake_dir, monkeypatch)
    assert build_verifier() == dll
    assert fake.calls == []


@pytest.mark.parametrize("stamp", [None, "0000000"], ids=["no-stamp", "other-commit"])
def test_dll_without_matching_commit_stamp_is_rebuilt(fake_dir, monkeypatch, stamp):
    fake_build(fake_dir, commit=stamp); fake = install(fake_dir, monkeypatch)
    assert build_verifier() == _dll_path(fake_dir)
    assert [c[0] for c in fake.calls] == ["git", "dotnet"]
    assert _dll_path(fake_dir).read_text() == "new dll"
    assert (fake_dir / "commit.txt").read_text().strip() == verify.VERIFIER_COMMIT


def test_garbled_stamp_is_rebuilt_not_a_crash(fake_dir, monkeypatch):
    fake_build(fake_dir); (fake_dir / "commit.txt").write_bytes(b"\xff\xfe\x00garbage")
    fake = install(fake_dir, monkeypatch)
    assert build_verifier() == _dll_path(fake_dir)
    assert [c[0] for c in fake.calls] == ["git", "dotnet"]
    assert (fake_dir / "commit.txt").read_text().strip() == verify.VERIFIER_COMMIT


def test_stamp_without_dll_is_not_a_finished_build(fake_dir, monkeypatch):
    fake_dir.mkdir(); (fake_dir / "commit.txt").write_text(verify.VERIFIER_COMMIT)
    fake = install(fake_dir, monkeypatch)
    build_verifier()
    assert [c[0] for c in fake.calls] == ["git", "dotnet"]


def test_force_rebuilds_even_when_finished(fake_dir, monkeypatch):
    fake_build(fake_dir); fake = install(fake_dir, monkeypatch)
    assert build_verifier(force=True) == _dll_path(fake_dir)
    assert [c[0] for c in fake.calls] == ["git", "dotnet"]
    assert _dll_path(fake_dir).read_text() == "new dll"
    assert debris(fake_dir) == []  # staging and the old build are gone


@pytest.mark.parametrize("leftover", ["src.tar", "simulation/Headless/Program.cs"])
def test_partial_earlier_build_is_rebuilt(fake_dir, monkeypatch, leftover):
    # src.tar left behind, or an extracted tree that never produced the DLL: rebuild from scratch.
    stale = fake_dir / leftover; stale.parent.mkdir(parents=True); stale.write_text("half done")
    fake = install(fake_dir, monkeypatch)
    dll = build_verifier()
    assert dll == _dll_path(fake_dir) and dll.is_file()
    assert [c[0] for c in fake.calls] == ["git", "dotnet"]
    assert not (fake_dir / "src.tar").exists()
    assert (fake_dir / "simulation" / "Headless" / "Program.cs").read_text() == "x"  # fresh extract, not the leftover
    assert debris(fake_dir) == []


def test_build_commands_use_the_pinned_commit_and_only_what_the_csproj_needs(fake_dir, monkeypatch):
    fake = install(fake_dir, monkeypatch)
    build_verifier()
    git, dotnet = fake.calls
    assert git[:3] == ["git", "archive", "--format=tar"]
    assert git[-3:] == ["e6119eb", "simulation/Assets/Simulation", "simulation/Headless"]
    assert dotnet[:2] == ["dotnet", "build"]
    assert Path(dotnet[2]).parent.parent.parent == fake_dir.parent  # built beside VERIFIER_DIR (the staging folder)
    assert Path(dotnet[2]).parent.parent.name.startswith("verifier.tmp-")
    assert "Release" in dotnet


def test_old_build_is_kept_until_the_new_one_has_finished(fake_dir, monkeypatch):
    fake_build(fake_dir); fake = install(fake_dir, monkeypatch)
    build_verifier(force=True)
    assert fake.old_build_present_during_dotnet is True


def test_failed_rebuild_leaves_the_old_build_usable_and_no_debris(fake_dir, monkeypatch):
    fake_build(fake_dir); fake = install(fake_dir, monkeypatch, fail_dotnet=True)
    with pytest.raises(RuntimeError, match="CS0001"):
        build_verifier(force=True)
    assert debris(fake_dir) == []
    fake.calls.clear()
    assert build_verifier() == _dll_path(fake_dir) and fake.calls == []  # old build still counts as built
    assert _dll_path(fake_dir).read_text() == "old dll"


def test_build_without_dll_raises(fake_dir, monkeypatch):
    install(fake_dir, monkeypatch, make_dll=False)
    with pytest.raises(RuntimeError, match="does not exist"):
        build_verifier()
    assert not fake_dir.exists() and debris(fake_dir) == []


def test_git_failure_raises_with_git_output_and_leaves_a_retryable_state(fake_dir, monkeypatch):
    monkeypatch.setattr(verify, "VERIFIER_COMMIT", "0123456789abcdef0123456789abcdef01234567")
    with pytest.raises(RuntimeError) as e:
        build_verifier()
    assert "git archive" in str(e.value) and "0123456789abcdef" in str(e.value)
    assert not fake_dir.exists() and debris(fake_dir) == []
    install(fake_dir, monkeypatch)
    assert build_verifier() == _dll_path(fake_dir)  # the next call starts over cleanly


def test_file_errors_during_a_build_become_runtime_errors(fake_dir, monkeypatch):
    def fail(folder):
        raise PermissionError("Access is denied")
    monkeypatch.setattr(verify, "_build_into", fail)
    with pytest.raises(RuntimeError, match="Access is denied"):
        build_verifier()


@pytest.mark.skipif(os.name != "nt", reason="Windows refuses to rename a folder holding an open file")
def test_build_in_use_raises_and_leaves_the_old_build_whole(fake_dir, monkeypatch):
    dll = fake_build(fake_dir); fake = install(fake_dir, monkeypatch)
    with open(dll, "rb"):  # what a running `dotnet TrafficHost.dll` does to the file
        with pytest.raises(RuntimeError, match="in use"):
            build_verifier(force=True)
    assert debris(fake_dir) == []
    assert dll.read_text() == "old dll" and (fake_dir / "commit.txt").is_file()
    fake.calls.clear()
    assert build_verifier() == dll and fake.calls == []  # untouched, still a finished build


def test_swap_failure_restores_the_old_build(fake_dir, monkeypatch):
    fake_build(fake_dir); fake = install(fake_dir, monkeypatch)
    real_replace = os.replace

    def replace(src, dst):
        if Path(src).name.startswith("verifier.tmp-"):
            raise PermissionError("Access is denied")
        return real_replace(src, dst)
    with monkeypatch.context() as m:
        m.setattr(verify.os, "replace", replace)
        with pytest.raises(RuntimeError, match="could not move"):
            build_verifier(force=True)
    assert debris(fake_dir) == []
    assert _dll_path(fake_dir).read_text() == "old dll" and verify._is_built()


def test_losing_the_race_to_another_builder_uses_their_build(fake_dir, monkeypatch):
    fake_build(fake_dir); install(fake_dir, monkeypatch)
    real_replace = os.replace

    def replace(src, dst):
        if Path(src).name.startswith("verifier.tmp-"):
            fake_build(fake_dir, content="theirs")  # another process lands its finished build first
            raise PermissionError("destination exists")
        return real_replace(src, dst)
    monkeypatch.setattr(verify.os, "replace", replace)
    assert build_verifier(force=True) == _dll_path(fake_dir)
    assert _dll_path(fake_dir).read_text() == "theirs"


def test_run_error_includes_tool_output():
    with pytest.raises(RuntimeError) as e:
        verify._run([sys.executable, "-c", "import sys; print('out-marker'); print('err-marker', file=sys.stderr); sys.exit(3)"])
    msg = str(e.value)
    assert "out-marker" in msg and "err-marker" in msg and "3" in msg


def test_run_missing_tool_is_a_runtime_error():
    with pytest.raises(RuntimeError, match="no-such-tool-xyz"):
        verify._run(["no-such-tool-xyz", "--version"])


def test_run_timeout_with_bytes_output_is_a_runtime_error(monkeypatch):
    # POSIX hands TimeoutExpired bytes (or None for an unused stream); mixing them must not raise TypeError.
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1, output=b"partial out", stderr=None)
    monkeypatch.setattr(verify.subprocess, "run", slow)
    with pytest.raises(RuntimeError, match="partial out"):
        verify._run(["dotnet", "build"], timeout=1)


# --- no host or dotnet needed: verify_recording's verdict rules, timeout and paths, with a fake "dotnet" ---

def _fake_verifier(monkeypatch, tmp_path, body: str) -> Path:
    """Replace `dotnet <dll>` with `python <script>`; the script plays the C# verifier. Returns a recording."""
    script = tmp_path / "fake_verifier.py"
    script.write_text(body)
    monkeypatch.setattr(verify, "build_verifier", lambda force=False: script)
    monkeypatch.setattr(verify, "DOTNET", sys.executable)
    rec = tmp_path / "rec.json"; rec.write_text("{}")
    return rec


def test_pass_needs_exit_zero_and_pass_on_stdout(monkeypatch, tmp_path):
    rec = _fake_verifier(monkeypatch, tmp_path,
                         "import sys; print('{\"result\":\"PASS\",\"args\":%r}' % sys.argv[1:])")
    ok, out = verify_recording(rec)
    assert ok is True
    assert "--verify-replay" in out and rec.name in out


def test_exit_one_is_a_rejection_verdict_with_the_verifiers_message(monkeypatch, tmp_path):
    rec = _fake_verifier(monkeypatch, tmp_path,
                         "import sys; print('PASS'); print('AI replay score/time diverged', file=sys.stderr); sys.exit(1)")
    ok, out = verify_recording(rec)
    assert ok is False  # exit 1 wins even if stdout says PASS
    assert "diverged" in out


@pytest.mark.parametrize("body", [
    "print('{\"result\":\"FAIL\"}')",
    "import sys; print('{\"result\":\"FAIL\"}'); print('PASS', file=sys.stderr)",
], ids=["no-pass", "pass-on-stderr-only"])
def test_exit_zero_without_pass_on_stdout_is_a_fault(monkeypatch, tmp_path, body):
    rec = _fake_verifier(monkeypatch, tmp_path, body)
    with pytest.raises(RuntimeError, match="exit code 0"):
        verify_recording(rec)


@pytest.mark.parametrize("code", [2, 127, 131, 255])
def test_other_exit_codes_are_faults_and_carry_the_output(monkeypatch, tmp_path, code):
    rec = _fake_verifier(monkeypatch, tmp_path,
                         f"import sys; print('PASS'); print('runtime exploded', file=sys.stderr); sys.exit({code})")
    with pytest.raises(RuntimeError) as e:
        verify_recording(rec)
    assert f"exit code {code}" in str(e.value) and "runtime exploded" in str(e.value)


def test_failure_to_start_dotnet_is_a_fault(monkeypatch, tmp_path):
    rec = _fake_verifier(monkeypatch, tmp_path, "print('PASS')")
    monkeypatch.setattr(verify, "DOTNET", "no-such-dotnet-xyz")
    with pytest.raises(RuntimeError, match="no-such-dotnet-xyz"):
        verify_recording(rec)


def test_build_failure_is_a_fault_not_a_verdict(monkeypatch, tmp_path):
    def fail(force=False):
        raise RuntimeError("dotnet build failed")
    monkeypatch.setattr(verify, "build_verifier", fail)
    rec = tmp_path / "r.json"; rec.write_text("{}")
    with pytest.raises(RuntimeError, match="dotnet build failed"):
        verify_recording(rec)


def test_missing_recording_is_a_verdict_even_without_a_verifier(monkeypatch, tmp_path):
    def fail(force=False):
        raise AssertionError("must not build for a missing file")
    monkeypatch.setattr(verify, "build_verifier", fail)
    ok, out = verify_recording(tmp_path / "gone.json")
    assert ok is False and "gone.json" in out


def test_timeout_raises_with_partial_output_and_kills_the_process(monkeypatch, tmp_path):
    rec = _fake_verifier(monkeypatch, tmp_path,
                         "import time; print('partial-marker', flush=True); time.sleep(60)")
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out") as e:
        verify_recording(rec, timeout=1.0)
    assert "partial-marker" in str(e.value)
    assert time.monotonic() - start < 20


def test_base_timeout_is_120_s_plus_2_s_per_action():
    assert verify.VERIFY_TIMEOUT_S == 120 and verify.PER_ACTION_TIMEOUT_S == 2


@pytest.mark.parametrize("n", [0, 1, 462, 1125, 3600])
def test_default_timeout_is_base_plus_two_seconds_per_action(tmp_path, n):
    p = tmp_path / "r.json"; p.write_text(json.dumps({"actions": [{}] * n, "seed": 1}))
    assert verify.default_timeout(p) == 120 + 2 * n


@pytest.mark.parametrize("content", [b"not json", b"\xff\xfe\x00 bad utf-8", b"[1, 2, 3]", b'{"actions": 5}',
                                     b'{"seed": 1}', b""], ids=["text", "bytes", "list", "scalar", "none", "empty"])
def test_default_timeout_falls_back_to_the_base(tmp_path, content):
    p = tmp_path / "r.json"; p.write_bytes(content)
    assert verify.default_timeout(p) == 120
    assert verify.default_timeout(tmp_path / "missing.json") == 120


def test_verify_recording_applies_the_default_timeout_formula(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout='{"result":"PASS"}', stderr="")
    monkeypatch.setattr(verify, "build_verifier", lambda force=False: Path("x.dll"))
    monkeypatch.setattr(verify.subprocess, "run", fake_run)
    rec = tmp_path / "r.json"; rec.write_text(json.dumps({"actions": [{}] * 1125}))
    assert verify_recording(rec)[0] is True
    assert seen["timeout"] == 120 + 2 * 1125
    verify_recording(rec, timeout=7)
    assert seen["timeout"] == 7


def test_relative_recording_path_reaches_dotnet_absolute(tmp_path, monkeypatch):
    rec = _fake_verifier(monkeypatch, tmp_path,
                         "import os, sys; print('PASS' if os.path.isabs(sys.argv[2]) else 'RELATIVE')")
    monkeypatch.chdir(tmp_path)
    ok, out = verify_recording(Path(rec.name))
    assert ok, out


def test_verifier_paths_are_absolute():
    assert verify.VERIFIER_DIR.is_absolute()
    assert verify.verifier_dll().is_absolute()
