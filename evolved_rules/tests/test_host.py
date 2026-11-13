import json
import sys
from pathlib import Path

import pytest
from evolved_rules.host import Host, HostError, ScenarioRejected, default_host_dll

@pytest.mark.host
def test_reset_returns_original_la(host):
    r = host.reset(1000)
    o = r["observation"]
    assert o["version"] == "OriginalReference" and o["unlimitedConstruction"] is False
    assert o["time"] == 0 and o["inventory"] == [25, 1, 0, 0, 0, 0]
    assert (o["width"], o["height"]) == (50, 30)

@pytest.mark.host
def test_step_20_advances_one_second(host):
    host.reset(1000)
    r = host.call(command="step", ticks=20)
    assert abs(r["observation"]["time"] - 1.0) < 1e-9

@pytest.mark.host
def test_error_reply_raises(host):
    host.reset(1000)
    with pytest.raises(HostError):
        host.call(command="nonsense")

def _fake(code: str, timeout: float = 5.0) -> Host:
    """A Host whose process is a tiny Python script instead of TrafficHost (no DLL or dotnet needed)."""
    h = Host.__new__(Host)
    h._start([sys.executable, "-c", code], timeout)
    return h


def _replies(*lines: dict) -> str:
    """Script for a fake host: read one request per reply, print the replies in order, then exit after one more
    line (close()'s quit) or at EOF."""
    return ("import sys\n"
            f"for line in {[json.dumps(r) for r in lines]!r}:\n"
            "    sys.stdin.readline()\n"
            "    print(line, flush=True)\n"
            "sys.stdin.readline()\n")


def _reset_reply(version="OriginalReference", unlimited=False, truncated=False, message=None):
    return {"accepted": True, "message": message, "terminated": False, "truncated": truncated,
            "observation": {"version": version, "unlimitedConstruction": unlimited, "time": 0}}


def test_call_times_out_and_raises():
    # A "host" that never answers: python sleeping. Host must raise HostError, not hang.
    h = _fake("import time; time.sleep(60)", timeout=0.5)
    try:
        with pytest.raises(HostError, match="no reply"):
            h.call(command="observe")
    finally:
        h.close()


def _jumping_clock(jump: float, at_call: int = 2):
    """time.monotonic() plus `jump` seconds from its `at_call`-th call on: a machine that slept mid-wait."""
    import time
    calls = [0]

    def clock():
        calls[0] += 1
        return time.monotonic() + (jump if calls[0] >= at_call else 0.0)
    return clock


def _slow_reply_script(delay: float) -> str:
    return ("import sys, time\n"
            "sys.stdin.readline()\n"
            f"time.sleep({delay})\n"
            "print('{\"ok\": true}', flush=True)\n"
            "sys.stdin.readline()\n")


def test_a_suspend_during_a_reply_wait_does_not_time_out():
    # The clock jumps 100 s at the first poll (the machine slept). Without the suspend rule that alone passes the
    # 3 s deadline; with it the deadline moves back and the reply, 2 s of awake time later, is taken.
    h = _fake(_slow_reply_script(2.0), timeout=3.0)
    h._clock = _jumping_clock(100.0)
    try:
        assert h.call(command="observe") == {"ok": True}
    finally:
        h.close()


def test_a_jump_inside_the_margin_still_counts_toward_the_timeout():
    # 5 s is within REPLY_SUSPEND_MARGIN_S (10 s): a slow pass, not a suspend, so the 3 s timeout fires.
    h = _fake(_slow_reply_script(30.0), timeout=3.0)
    h._clock = _jumping_clock(5.0)
    try:
        with pytest.raises(HostError, match="no reply"):
            h.call(command="observe")
    finally:
        h.close()


def test_a_silent_host_still_times_out_after_a_suspend():
    # After the suspend is forgiven, a host that never answers still fails after timeout s of awake time.
    import time
    h = _fake("import time; time.sleep(60)", timeout=1.5)
    h._clock = _jumping_clock(100.0)
    t0 = time.monotonic()
    try:
        with pytest.raises(HostError, match="no reply"):
            h.call(command="observe")
    finally:
        h.close()
    assert 1.4 <= time.monotonic() - t0 < 5.0


def test_host_exiting_mid_call_raises_then_every_call_raises():
    h = _fake("import sys; sys.stdin.readline()")  # reads the request, exits without replying (EOF)
    try:
        with pytest.raises(HostError, match="exited"):
            h.call(command="observe")
        with pytest.raises(HostError, match="not running"):
            h.call(command="observe")
        with pytest.raises(HostError, match="not running"):
            h.reset(1000)
    finally:
        h.close()


def test_call_to_a_dead_process_raises():
    h = _fake("pass")  # exits at once
    try:
        h._proc.wait(timeout=10)
        with pytest.raises(HostError, match="not running"):
            h.call(command="observe")
    finally:
        h.close()


def test_unparseable_reply_raises_and_kills_the_host():
    h = _fake("import sys; sys.stdin.readline(); print('not json', flush=True); sys.stdin.readline()")
    try:
        with pytest.raises(HostError, match="unparseable"):
            h.call(command="observe")
        assert h._proc.poll() is not None
        with pytest.raises(HostError, match="not running"):
            h.call(command="observe")
    finally:
        h.close()


def test_truncated_reset_raises_scenario_rejected():
    h = _fake(_replies(_reset_reply(truncated=True, message="infeasible")))
    try:
        with pytest.raises(ScenarioRejected, match="infeasible"):
            h.reset(1000)
    finally:
        h.close()
    assert issubclass(ScenarioRejected, HostError)


@pytest.mark.parametrize("version, unlimited", [("Custom", False), ("OriginalReference", True)])
def test_reset_rejects_other_rules(version, unlimited):
    h = _fake(_replies(_reset_reply(version=version, unlimited=unlimited)))
    try:
        with pytest.raises(HostError, match="unexpected rules"):
            h.reset(1000)
    finally:
        h.close()


def test_reset_sends_original_reference_and_accepts_its_reply():
    h = _fake("import sys, json\n"
              "req = json.loads(sys.stdin.readline())\n"
              f"reply = {json.dumps(_reset_reply())!r}\n"
              "out = json.loads(reply); out['echo'] = req\n"
              "print(json.dumps(out), flush=True)\n"
              "sys.stdin.readline()\n")
    try:
        reply = h.reset(1234)
        assert reply["echo"] == {"command": "reset", "version": "OriginalReference", "scenario": "LosAngeles",
                                 "seed": 1234}
    finally:
        h.close()


def test_close_twice_is_harmless():
    h = _fake(_replies())
    h.close()
    assert h._proc.poll() is not None
    h.close()
    with pytest.raises(HostError, match="not running"):
        h.call(command="observe")

def test_default_host_dll_env_override(monkeypatch):
    monkeypatch.setenv("EVOLVED_RULES_HOST_DLL", str(Path("somewhere") / "Custom.dll"))
    assert default_host_dll() == Path("somewhere") / "Custom.dll"
    monkeypatch.setenv("EVOLVED_RULES_HOST_DLL", "")  # empty counts as unset
    assert default_host_dll().name == "TrafficHost.dll"
    monkeypatch.delenv("EVOLVED_RULES_HOST_DLL", raising=False)
    assert default_host_dll().parts[-5:] == ("Headless", "bin", "Release", "net8.0", "TrafficHost.dll")


@pytest.mark.parametrize("scenario", ["ReferenceLab", "losangeles", "0"])
def test_reset_refuses_other_scenarios_before_sending(scenario):
    # The fake replies to exactly one request: if the bad reset were sent, the good one would get no reply.
    h = _fake(_replies(_reset_reply()))
    try:
        with pytest.raises(ValueError, match="scenario"):
            h.reset(1000, scenario)
        assert h.reset(1000, "LosAngeles")["observation"]["version"] == "OriginalReference"
    finally:
        h.close()


def test_the_default_reply_timeout_is_two_minutes():  # gp-6: hosts stall on battery
    import inspect
    from evolved_rules.host import REPLY_TIMEOUT_S
    assert REPLY_TIMEOUT_S == 120.0
    assert inspect.signature(Host.__init__).parameters["timeout"].default == REPLY_TIMEOUT_S
