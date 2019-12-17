import pytest

from debmonitor import middleware


VALID_DN_STRINGS = (
    'cn=host1.example.com',
    'CN=host1.example.com',
    'CN=host1.example.com,O=Acme,C=US',
    'O=Acme,CN=host1.example.com,C=US',
    'O=Acme,C=US,CN=host1.example.com',
    r'CN=host1.example.com,O=Acme\, US,C=US',
    r'O=Acme\, US,CN=host1.example.com,C=US',
    r'O=Acme\, US,C=US,CN=host1.example.com',
)
INVALID_DN_STRINGS = (
    '',
    'O=host1.example.com',
    'CN = host1.example.com',
    'O=Acme, CN=host1.example.com, C=US',
    'O=Acme, C=US, CN=host1.example.com',
)


@pytest.mark.parametrize('dn', VALID_DN_STRINGS)
def test_get_host_cn_ok(dn):
    """For all DNs with a valid CN get_host_cn() should return the CN of the client."""
    assert middleware.get_host_cn(dn) == 'host1.example.com'


@pytest.mark.parametrize('dn', INVALID_DN_STRINGS)
def test_get_host_cn_ko(dn):
    """For all DNs with an invalid CN get_host_cn() should return None."""
    assert middleware.get_host_cn(dn) is None


def test_is_valid_cn_ok():
    """Calling is_valid_cn() should return True if the cn is valid for that name."""
    assert middleware.is_valid_cn('host1.example.com', 'host1.example.com')


def test_is_valid_cn_ko():
    """Calling is_valid_cn() should return False if the cn is not valid for that name."""
    assert not middleware.is_valid_cn('invalid_cn', 'host1.example.com')


def test_is_valid_cn_proxy(settings):
    """Calling is_valid_cn() should return True if the cn of a proxy is valid for that name."""
    settings.DEBMONITOR_PROXY_HOSTS = ['proxy.example.com']
    assert middleware.is_valid_cn('proxy.example.com', 'host1.example.com')
