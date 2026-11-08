"""gp-5: the replay verifier is built from the simulator the games are played on."""
import pytest

from evolved_rules import verify
from evolved_rules.host import PRE_VERSIONING, default_host_dll, simulator_version


@pytest.mark.host
def test_the_verifier_and_the_playing_host_are_the_same_simulator(host_dll, verifier):
    played = simulator_version(default_host_dll())
    assert played != PRE_VERSIONING
    assert simulator_version(verify.build_verifier()) == played
