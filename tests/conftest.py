import pytest
import requests_mock

from django.core.management import call_command


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/db.json')


@pytest.fixture()
def mocked_requests():
    """Set mocked requests fixture."""
    with requests_mock.Mocker() as mocker:
        yield mocker
