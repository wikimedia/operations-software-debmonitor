import sys

import pytest
import requests_mock

try:  # Python3
    import unittest.mock as mock
except ImportError:  # Python2
    import mock


if sys.version_info.major >= 3:  # Would fail for CLI tests in Python2
    from django.core.management import call_command


HOSTNAME = 'host1.example.com'


@pytest.mark.skipif(sys.version_info.major < 3, reason='Requires Python3 or greater')
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/db.json')


@pytest.fixture()
def mocked_requests():
    """Set mocked requests fixture."""
    with requests_mock.Mocker() as mocker:
        yield mocker


@pytest.fixture()
def mocked_getfqdn():
    """Set the getfqdn mock fixture."""
    with mock.patch('socket.getfqdn', return_value=HOSTNAME) as mocker:
        yield mocker
