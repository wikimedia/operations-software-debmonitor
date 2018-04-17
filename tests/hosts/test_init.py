import pytest

import hosts


VALID_DN_STRINGS = (
    'cn=host1.example.com',
    'CN=host1.example.com',
    'CN=host1.example.com,O=Acme,C=US',
    'O=Acme,CN=host1.example.com,C=US',
    'O=Acme,C=US,CN=host1.example.com',
    'CN=host1.example.com,O=Acme\, US,C=US',
    'O=Acme\, US,CN=host1.example.com,C=US',
    'O=Acme\, US,C=US,CN=host1.example.com',
)
INVALID_DN_STRINGS = (
    '',
    'CN=host2.example.com',
    'O=host1.example.com',
    'CN = host1.example.com',
    'O=Acme, CN=host1.example.com, C=US',
    'O=Acme, C=US, CN=host1.example.com',
)


@pytest.mark.parametrize('dn', VALID_DN_STRINGS)
def test_is_valid_cn_ok(dn):
    """For all DNs with a valid CN is_valid_cn() should return True."""
    assert hosts.is_valid_cn(dn, 'host1.example.com') is True


@pytest.mark.parametrize('dn', INVALID_DN_STRINGS)
def test_is_valid_cn_ko(dn):
    """For all DNs with an invalid CN is_valid_cn() should return False."""
    assert hosts.is_valid_cn(dn, 'host1.example.com') is False
