from unittest.mock import patch, mock_open

import debmonitor


CLIENT_VERSION = '0.1.2'
CLIENT_CHECKSUM_DUMMY = 'bc45bcc2f37b13995fa4d7ae82cecd6e'
CLIENT_BODY_DUMMY = """import os
__version__ = '0.1.2'
"""
CLIENT_BODY_NO_VERSION = 'import os'
CLIENT_CHECKSUM_NO_VERSION = 'ed9f4b8f879ddbb59fda1057ea3a2810'


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_NO_VERSION))
def test_get_client_no_version():
    """Calling get_client() should return the client with its version (default to empty string) and checksum."""
    version, checksum, body = debmonitor.get_client()

    assert version == ''
    assert checksum == CLIENT_CHECKSUM_NO_VERSION
    assert body == CLIENT_BODY_NO_VERSION


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_DUMMY))
def test_get_client():
    """Calling get_client() should return the client with its version and checksum."""
    version, checksum, body = debmonitor.get_client()

    assert version == CLIENT_VERSION
    assert checksum == CLIENT_CHECKSUM_DUMMY
    assert body == CLIENT_BODY_DUMMY
