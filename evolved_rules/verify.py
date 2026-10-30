"""Replay verifier: builds the headless `--verify-replay` mode and runs recordings through it.

HEAD's simulation/Headless/Program.cs no longer has `--verify-replay`, but commit e6119eb (Mohammad's 28 Oct
run) does, and its simulation code is identical to ours (PLAN section 6). It is built from `git archive`
into an ignored output folder: no branch is ever checked out, and nothing under simulation/ is touched.

Contract of the C# mode (Program.cs at e6119eb, the `--verify-replay` block): it prints one JSON line with
`"result":"PASS"` and exits 0 when AiReplaySession replays every command with the recorded acceptance, trips
and time and the same final outcome. Any exception (unreadable or empty recording, a diverging command or
outcome) is caught there: the message goes to stderr, nothing to stdout, and `Environment.ExitCode=1`.
Exit code 1 is therefore the only verdict "this recording is rejected"; every other result is a fault.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path

from .host import ROOT

VERIFIER_COMMIT = "e6119eb"
VERIFIER_DIR = ROOT / "output" / "evolved_rules" / "verifier"  # /output/ is git-ignored

# TrafficHost.csproj only compiles ../Assets/Simulation/*.cs next to the Headless folder, so these two
# folders are the whole build input (checked: nothing else under simulation/ is needed).
ARCHIVE_PATHS = ("simulation/Assets/Simulation", "simulation/Headless")
DLL_RELATIVE = Path("simulation") / "Headless" / "bin" / "Release" / "net8.0" / "TrafficHost.dll"
COMMIT_STAMP = "commit.txt"  # written last, after a successful build: the commit the folder was built from

DOTNET = "dotnet"
GIT = "git"
BUILD_TIMEOUT_S = 600.0  # Windows: a timed-out build can overrun this while the compiler child exits (it is never orphaned)
GIT_TIMEOUT_S = 120.0

# A replay's cost grows faster than linearly with game length (the city and its cars grow): Mohammad's
# 1125-action game takes about 35 s, 900-action games 50-60 s under load. So the budget is a base plus a
# per-action allowance, and running out of it is a fault (RuntimeError), never a verdict.
VERIFY_TIMEOUT_S = 120.0
PER_ACTION_TIMEOUT_S = 2.0

REJECTED_EXIT_CODE = 1  # Program.cs: the catch block sets Environment.ExitCode=1


def _text(value) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")


def _cannot_run(tool, error: Exception) -> RuntimeError:
    return RuntimeError(f"cannot run {str(tool)!r} (is it installed and on PATH?): {error}")


def _run(argv: list[str], *, cwd: Path | None = None, timeout: float = GIT_TIMEOUT_S) -> str:
    """Run a tool to completion and return its combined output; RuntimeError (with the output) on any failure.

    Output is decoded as UTF-8 with replacement, like host.py: the verdict is unaffected, but non-ASCII
    diagnostics from .NET (console code page) can come back garbled.
    """
    cmd = " ".join(map(str, argv))
    try:
        proc = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError as e:
        raise _cannot_run(argv[0], e) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{cmd} timed out after {timeout:g} s\n{_text(e.stdout) + _text(e.stderr)}") from e
    except OSError as e:
        raise RuntimeError(f"cannot run {cmd}: {e}") from e
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd} failed with exit code {proc.returncode}\n{output}")
    return output


def _remove_tree(path: Path) -> None:
    """rmtree that also deletes read-only files (extracted from git archive, or written by dotnet)."""
    def make_writable_and_retry(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onexc=make_writable_and_retry)


def _discard(path: Path) -> None:
    """Best-effort delete of a folder nobody needs (a failed staging build, a replaced old build)."""
    if path.exists():
        try:
            _remove_tree(path)
        except OSError:
            pass


def verifier_dll() -> Path:
    return VERIFIER_DIR / DLL_RELATIVE


def _is_built() -> bool:
    """A finished build of VERIFIER_COMMIT: the DLL is there and the stamp (written last) names the commit."""
    try:
        stamp = (VERIFIER_DIR / COMMIT_STAMP).read_text(encoding="utf-8").strip()
    except (OSError, ValueError):  # ValueError: a garbled, non-UTF-8 stamp is just "not built"
        return False
    return stamp == VERIFIER_COMMIT and verifier_dll().is_file()


def _sibling(kind: str) -> Path:
    return VERIFIER_DIR.with_name(f"{VERIFIER_DIR.name}.{kind}-{os.getpid()}")


def _build_into(folder: Path) -> None:
    folder.mkdir(parents=True)
    tar_path = folder / "src.tar"
    # Run in the repo found from this package, not the process cwd. git archive only reads objects.
    _run([GIT, "archive", "--format=tar", "-o", tar_path, VERIFIER_COMMIT, *ARCHIVE_PATHS], cwd=ROOT)
    with tarfile.open(tar_path) as tar:
        tar.extractall(folder, filter="data")
    tar_path.unlink()
    project = folder / "simulation" / "Headless"
    # --disable-build-servers: no MSBuild / compiler server is left running after the build.
    _run([DOTNET, "build", project, "-c", "Release", "--disable-build-servers"], timeout=BUILD_TIMEOUT_S)
    if not (folder / DLL_RELATIVE).is_file():
        raise RuntimeError(f"dotnet build succeeded but {folder / DLL_RELATIVE} does not exist")
    (folder / COMMIT_STAMP).write_text(VERIFIER_COMMIT + "\n", encoding="utf-8")


def _swap_in(staged: Path) -> None:
    """Replace VERIFIER_DIR by the finished build in `staged`.

    The old folder is renamed aside whole, never deleted in place: Windows refuses to rename a folder that
    holds an open file (a running verification has TrafficHost.dll open), and then nothing has changed, so
    the old build stays complete. VERIFIER_DIR is therefore always either a complete build or absent.
    """
    old = _sibling("old")
    _discard(old)
    moved_aside = False
    if VERIFIER_DIR.exists():
        try:
            os.replace(VERIFIER_DIR, old)
        except OSError as e:
            raise RuntimeError(f"verifier is in use; close running verifications and retry ({e})") from e
        moved_aside = True
    try:
        os.replace(staged, VERIFIER_DIR)
    except OSError as e:
        restored = False
        if moved_aside and not VERIFIER_DIR.exists():
            try:
                os.replace(old, VERIFIER_DIR)
                restored = True
            except OSError:
                pass
        if not restored and _is_built():
            return  # another process finished the same build first; use theirs
        raise RuntimeError(f"could not move the new verifier build into {VERIFIER_DIR}: {e}") from e
    finally:
        _discard(old)  # the replaced build; already gone if it was restored


def build_verifier(force: bool = False) -> Path:
    """Build the e6119eb verifier once and return TrafficHost.dll; later calls reuse it.

    "Built" means the DLL exists and `commit.txt` names VERIFIER_COMMIT (so a changed commit rebuilds by
    itself, and an old or half-removed tree never counts). A rebuild happens in a sibling folder
    (`verifier.tmp-<pid>`) and replaces VERIFIER_DIR only once it has fully succeeded. Raises RuntimeError,
    with the tool's output, if git or dotnet fails, and if the old build cannot be replaced because it is in
    use. There is no cross-process lock: two simultaneous first builds each build their own copy and the
    second to finish keeps the first one's.
    """
    if not force and _is_built():
        return verifier_dll()
    staged = _sibling("tmp")
    try:
        VERIFIER_DIR.parent.mkdir(parents=True, exist_ok=True)
        _discard(staged)
        _build_into(staged)
        _swap_in(staged)
    except OSError as e:
        raise RuntimeError(f"could not build the verifier in {VERIFIER_DIR}: {e}") from e
    finally:
        _discard(staged)  # nothing left after a successful swap; the debris of a failed build otherwise
    return verifier_dll()


def default_timeout(path: Path) -> float:
    """VERIFY_TIMEOUT_S plus PER_ACTION_TIMEOUT_S per action in the recording; the base if it cannot be read."""
    try:
        actions = json.loads(Path(path).read_text(encoding="utf-8")).get("actions")
    except (OSError, ValueError, AttributeError, RecursionError):  # unreadable, not JSON, not an object
        return VERIFY_TIMEOUT_S
    return VERIFY_TIMEOUT_S + PER_ACTION_TIMEOUT_S * (len(actions) if isinstance(actions, list) else 0)


def verify_recording(path: Path, timeout: float | None = None) -> tuple[bool, str]:
    """Replay a recording with `--verify-replay`. Returns (passed, stdout + stderr).

    (True, out): exit code 0 and PASS on stdout (PLAN section 6).
    (False, out): the verifier rejected the recording, i.e. it exited with code 1 (a replay that diverges, an
    empty or unreadable recording), or the recording file does not exist (a verdict about the input).
    RuntimeError, with the output: anything else is a fault in the verifier, not a verdict on the recording.
    That covers a build failure, dotnet failing to start, any other exit code (a corrupt DLL or missing
    runtime), exit 0 without PASS, and running out of time.

    timeout (seconds) defaults to default_timeout(path): 120 s + 2 s per action in the recording.
    """
    path = Path(path)
    if not path.is_file():
        return False, f"recording not found: {path}"
    limit = default_timeout(path) if timeout is None else timeout
    dll = build_verifier()
    argv = [DOTNET, str(dll), "--verify-replay", str(path.resolve())]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=limit)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"verifier timed out after {limit:g} s on {path} (a timeout is not a verdict)\n"
                           f"{_text(e.stdout) + _text(e.stderr)}") from e
    except OSError as e:
        raise _cannot_run(DOTNET, e) from e
    output = proc.stdout + proc.stderr
    if proc.returncode == 0 and "PASS" in proc.stdout:
        return True, output
    if proc.returncode == REJECTED_EXIT_CODE:
        return False, output
    raise RuntimeError(f"verifier fault on {path}: exit code {proc.returncode}, expected 0 with PASS on stdout "
                       f"or {REJECTED_EXIT_CODE} for a rejection\n{output}")
