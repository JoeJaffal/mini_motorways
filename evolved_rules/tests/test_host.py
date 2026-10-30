from pathlib import Path

import pytest
from evolved_rules.host import Host, HostError, default_host_dll

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

def test_call_times_out_and_raises(tmp_path):
    # A "host" that never answers: python sleeping. Host must raise HostError, not hang.
    h = Host.__new__(Host)
    h._start(["py", "-3.12", "-c", "import time; time.sleep(60)"], timeout=0.5)
    with pytest.raises(HostError):
        h.call(command="observe")
    h.close()

def test_default_host_dll_env_override(monkeypatch):
    monkeypatch.setenv("EVOLVED_RULES_HOST_DLL", str(Path("somewhere") / "Custom.dll"))
    assert default_host_dll() == Path("somewhere") / "Custom.dll"
    monkeypatch.setenv("EVOLVED_RULES_HOST_DLL", "")  # empty counts as unset
    assert default_host_dll().name == "TrafficHost.dll"
    monkeypatch.delenv("EVOLVED_RULES_HOST_DLL", raising=False)
    assert default_host_dll().parts[-5:] == ("Headless", "bin", "Release", "net8.0", "TrafficHost.dll")
