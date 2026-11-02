"""Keep-awake helper (sleep-safe runs): the Windows execution-state flags, restore, failure and nesting."""
from __future__ import annotations

import sys
import types

import pytest

from evolved_rules import power


class FakeApi:
    """Stands in for kernel32.SetThreadExecutionState: records every call, returns `result(flags)`."""

    def __init__(self, result=lambda flags: 0x80000000):
        self.calls: list[int] = []
        self.result = result

    def __call__(self, flags):
        self.calls.append(flags)
        return self.result(flags)


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(power, "_api", lambda: fake)
    return fake


def test_flag_values_are_the_windows_constants():
    assert power.ES_CONTINUOUS == 0x80000000
    assert power.ES_SYSTEM_REQUIRED == 0x00000001
    assert power.ES_AWAYMODE_REQUIRED == 0x00000040
    assert power.KEEP_AWAKE == 0x80000041


def test_keep_awake_sets_the_flags_and_restores_on_exit(api):
    with power.keep_awake() as held:
        assert held is True
        assert api.calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED | power.ES_AWAYMODE_REQUIRED]
    assert api.calls[-1] == power.ES_CONTINUOUS and len(api.calls) == 2


def test_keep_awake_restores_on_an_exception(api):
    with pytest.raises(KeyboardInterrupt):
        with power.keep_awake():
            raise KeyboardInterrupt
    assert api.calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS]


def test_a_refused_away_mode_falls_back_to_system_required(api):
    api.result = lambda flags: 0 if flags & power.ES_AWAYMODE_REQUIRED else 0x80000000
    with power.keep_awake() as held:
        assert held is True
    assert api.calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED, power.ES_CONTINUOUS]


def test_a_failing_api_is_tolerated(api, capsys):
    api.result = lambda flags: 0
    with power.keep_awake() as held:
        assert held is False
    assert "keep-awake" in capsys.readouterr().err
    assert api.calls[-1] == power.ES_CONTINUOUS  # restoring is always safe


def test_an_api_that_raises_is_tolerated(monkeypatch, capsys):
    def boom(flags):
        raise OSError("no kernel32")

    monkeypatch.setattr(power, "_api", lambda: boom)
    with power.keep_awake() as held:
        assert held is False
    assert "keep-awake" in capsys.readouterr().err


def test_nested_use_sets_and_restores_once(api):
    with power.keep_awake():
        with power.keep_awake() as inner:
            assert inner is True
        assert api.calls == [power.KEEP_AWAKE]  # the inner exit leaves the outer request in place
    assert api.calls == [power.KEEP_AWAKE, power.ES_CONTINUOUS]


def test_no_op_off_windows(monkeypatch):
    monkeypatch.setattr(power, "sys", types.SimpleNamespace(platform="linux", stderr=sys.stderr))
    assert power._api() is None
    with power.keep_awake() as held:
        assert held is False


def test_api_lookup_uses_kernel32(monkeypatch):
    seen = {}

    class Fn:
        def __call__(self, flags):
            return 1

    def windll(name, **kw):
        seen["dll"] = name
        return types.SimpleNamespace(SetThreadExecutionState=Fn())

    monkeypatch.setattr(power, "sys", types.SimpleNamespace(platform="win32", stderr=sys.stderr))
    monkeypatch.setattr(power.ctypes, "WinDLL", windll, raising=False)
    fn = power._api()
    assert seen["dll"] == "kernel32" and fn(power.KEEP_AWAKE) == 1
    assert fn.restype is power.ctypes.c_uint32 and fn.argtypes == [power.ctypes.c_uint32]


@pytest.mark.skipif(sys.platform != "win32", reason="the real API exists on Windows only")
def test_the_real_api_accepts_the_request():
    with power.keep_awake() as held:
        assert held is True
