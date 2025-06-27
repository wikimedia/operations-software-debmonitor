import pytest

from django.urls import resolve, reverse

from debmonitor import views
from tests.conftest import setup_auth_settings, validate_status_code

INDEX_URL = '/'
SEARCH_URL = '/search'


def test_index_reverse_url():
    """Reversing the homepage URL name should return the correct URL."""
    url = reverse('index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the homepage should return a 200 OK if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the homepage should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_search_reverse_url():
    """Reversing the search results URL name should return the correct URL."""
    url = reverse('search')
    assert url == SEARCH_URL


@pytest.mark.django_db
def test_search_status_code(client, settings, require_login, verify_clients):
    """Requesting the search result page should return a 200 OK if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(SEARCH_URL)
    validate_status_code(response, require_login)


def test_search_view_function():
    """Resolving the URL for the search results should return the correct view."""
    view = resolve(SEARCH_URL)
    assert view.func is views.search


def test_search_invalid(client, settings, require_login, verify_clients):
    """A GET to the search endpoint should return 200 also with an invalid query, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(SEARCH_URL + '?q=a')
    validate_status_code(response, require_login)
    if response.status_code == 200:
        assert 'Invalid search query' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_search_valid(client, settings, require_login, verify_clients):
    """A GET to the search endpoint should return 200 with a valid query, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(SEARCH_URL + '?q=1.0')
    validate_status_code(response, require_login)
    if response.status_code == 200:
        assert 'Invalid search query' not in response.content.decode('utf-8')
        assert 'href="/packages/package1"' in response.content.decode('utf-8')


def test_auth_check(client, settings, require_login, verify_clients):
    """Requesting the auth-check endpoint should return OK if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get('/auth-check')
    validate_status_code(response, require_login, verify_clients=verify_clients)
    if not require_login and not verify_clients:
        assert response.content.decode().strip() == "OK"
