import pytest

from django.urls import resolve, reverse

from kubernetes import views
from tests.conftest import setup_auth_settings, validate_status_code


INDEX_URL = '/kubernetes/'


def test_index_reverse_url():
    """Reversing the kubernetes index page URL name should return the correct URL."""
    url = reverse('kubernetes:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the kubernetes index page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the kubernetes index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index
