import sys

import pytest
import requests_mock

try:  # Python3
    import unittest.mock as mock
except ImportError:  # Python2
    import mock


if sys.version_info.major >= 3 and sys.version_info.minor >= 5:  # Would fail for CLI tests in Python 2.7 and 3.4
    from django.core.management import call_command


HOSTNAME = 'host1.example.com'
IMAGEBASENAME = 'registry.example.com/component/image-name:'
IMAGENAME = '{base}1.2.3-1'.format(base=IMAGEBASENAME)
STRONGHOLD_MIDDLEWARE = 'stronghold.middleware.LoginRequiredMiddleware'


@pytest.mark.skipif(sys.version_info.major < 3 or sys.version_info.major == 3 and sys.version_info.minor < 5,
                    reason='Requires Python3.5 or greater')
@pytest.fixture(scope='module')
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


def pytest_generate_tests(metafunc):
    """Inject parametrization for common parameters."""
    for param in ('require_login', 'verify_clients'):
        if param in metafunc.fixturenames:
            metafunc.parametrize(param, (False, True))


def validate_status_code(response, require_login, verify_clients=False, default=200):
    """Helper function for tests to validate the HTTP status code based on global settings."""
    ret = default
    if verify_clients:
        ret = 403
    elif require_login:
        ret = 302

    assert response.status_code == ret


def setup_auth_settings(settings, require_login, verify_clients):
    """Helper function for tests to set up the authentication settings based on test parametrization."""
    settings.DEBMONITOR_VERIFY_CLIENTS = verify_clients
    if require_login:
        settings.MIDDLEWARE = list(settings.MIDDLEWARE) + [STRONGHOLD_MIDDLEWARE]
