import shutil
import subprocess

import pytest

from evolved_rules import verify
from evolved_rules.host import ROOT, Host, default_host_dll

MOHAMMAD_REF = "upstream/mohammad"


@pytest.fixture(autouse=True)
def _pinned_simulator_version(request, monkeypatch):
    """gp-5: outside real-host tests the engine keys results on helpers.TEST_SIM, the version fake games report."""
    if request.node.get_closest_marker("host") is None:
        from evolved_rules import engine as en
        from evolved_rules.tests.helpers import TEST_SIM
        monkeypatch.setattr(en, "_simulator_version", lambda: TEST_SIM)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "host: needs external tools: the built C# TrafficHost (Release DLL and dotnet), the replay verifier "
        "(dotnet, plus git and commit e6119eb unless it is already built) or the upstream/mohammad ref; "
        "skips when they are missing")


def _git_resolves(rev: str) -> bool:
    """`git rev-parse --verify` on rev in this repo; False when git is missing or the rev does not exist."""
    if shutil.which("git") is None:
        return False
    try:
        out = subprocess.run(["git", "rev-parse", "--verify", "--quiet", rev], cwd=ROOT, capture_output=True,
                             timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def skip_without_host_dll() -> None:
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet is not on PATH")
    if not default_host_dll().exists():
        pytest.skip(f"TrafficHost Release DLL not built ({default_host_dll()}; "
                    "dotnet build simulation/Headless -c Release)")


def skip_without_verifier() -> None:
    """The verifier needs dotnet, and to build it, git and commit e6119eb (verify.build_verifier)."""
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet is not on PATH (needed by the replay verifier)")
    if not verify._is_built() and not _git_resolves(f"{verify.VERIFIER_COMMIT}^{{commit}}"):
        pytest.skip(f"the replay verifier is not built and git cannot read commit {verify.VERIFIER_COMMIT}")


def skip_without_mohammad_ref() -> None:
    if not _git_resolves(MOHAMMAD_REF):
        pytest.skip(f"git ref {MOHAMMAD_REF} is not available (git rev-parse --verify {MOHAMMAD_REF})")


@pytest.fixture
def host_dll():
    """Skips unless dotnet and the Release TrafficHost DLL are there (for tests that start hosts themselves)."""
    skip_without_host_dll()


@pytest.fixture
def verifier():
    """Skips unless the replay verifier can run (dotnet; git and e6119eb if it still has to be built)."""
    skip_without_verifier()


@pytest.fixture
def mohammad_ref():
    """Skips unless git can resolve upstream/mohammad (Mohammad's recorded games)."""
    skip_without_mohammad_ref()


@pytest.fixture
def host():
    skip_without_host_dll()
    with Host() as h:
        yield h
