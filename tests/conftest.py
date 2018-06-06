import sys

import pytest
import requests_mock

if sys.version_info.major >= 3:  # Would fail for CLI tests in Python2
    from django.core.management import call_command


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
