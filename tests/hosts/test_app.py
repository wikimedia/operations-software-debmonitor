from hosts.apps import HostsConfig


def test_apps():
    assert HostsConfig.name == 'hosts'
