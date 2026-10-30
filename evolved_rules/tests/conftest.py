import pytest

from evolved_rules.host import Host, default_host_dll


def pytest_configure(config):
    config.addinivalue_line("markers", "host: test needs the built C# TrafficHost")


@pytest.fixture
def host():
    if not default_host_dll().exists():
        pytest.skip("TrafficHost Release DLL not built (dotnet build simulation/Headless -c Release)")
    with Host() as h:
        yield h
