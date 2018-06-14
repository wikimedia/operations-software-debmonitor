from unittest.mock import patch, mock_open

import debmonitor

from tests import debmonitor as tests_deb


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_NO_VERSION))
def test_get_client_no_version():
    """Calling get_client() should return the client with its version (default to empty string) and checksum."""
    version, checksum, body = debmonitor.get_client()

    assert version == ''
    assert checksum == tests_deb.CLIENT_CHECKSUM_NO_VERSION
    assert body == tests_deb.CLIENT_BODY_NO_VERSION


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_DUMMY_1))
def test_get_client():
    """Calling get_client() should return the client with its version and checksum."""
    version, checksum, body = debmonitor.get_client()

    assert version == tests_deb.CLIENT_VERSION
    assert checksum == tests_deb.CLIENT_CHECKSUM_DUMMY_1
    assert body == tests_deb.CLIENT_BODY_DUMMY_1
