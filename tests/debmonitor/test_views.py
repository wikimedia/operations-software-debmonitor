from unittest.mock import patch, mock_open

import pytest

from django.urls import resolve, reverse

from debmonitor import views
from debmonitor.middleware import SSL_CLIENT_VERIFY_HEADER, SSL_CLIENT_VERIFY_SUCCESS
from tests import debmonitor as tests_deb
from tests.conftest import setup_auth_settings, validate_status_code

INDEX_URL = '/'
CLIENT_URL = '/client'
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


def test_client_reverse_url():
    """Reversing the client URL name should return the correct URL."""
    url = reverse('client')
    assert url == CLIENT_URL


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_NO_VERSION))
def test_client_get_no_version(client, settings, require_login, verify_clients):
    """A GET to the client endpoint should return the client and its checksum also if the version is not set."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(CLIENT_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients)

    if response.status_code == 200:
        assert response[views.CLIENT_VERSION_HEADER] == ''
        assert response[views.CLIENT_CHECKSUM_HEADER] == tests_deb.CLIENT_CHECKSUM_NO_VERSION
        assert response.content.decode('utf-8') == tests_deb.CLIENT_BODY_NO_VERSION
    else:
        assert views.CLIENT_VERSION_HEADER not in response
        assert views.CLIENT_CHECKSUM_HEADER not in response
        if response.status_code == 403:
            assert 'Client certificate validation failed' in response.content.decode('utf-8')


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_DUMMY_1))
def test_client_get(client, settings, require_login, verify_clients):
    """A GET to the client endpoint should return the client with its version and checksum, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(CLIENT_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients)

    if response.status_code == 200:
        assert response[views.CLIENT_VERSION_HEADER] == tests_deb.CLIENT_VERSION
        assert response[views.CLIENT_CHECKSUM_HEADER] == tests_deb.CLIENT_CHECKSUM_DUMMY_1
        assert response.content.decode('utf-8') == tests_deb.CLIENT_BODY_DUMMY_1
    else:
        assert views.CLIENT_VERSION_HEADER not in response
        assert views.CLIENT_CHECKSUM_HEADER not in response
        if response.status_code == 403:
            assert 'Client certificate validation failed' in response.content.decode('utf-8')


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_DUMMY_2))
def test_client_head(client, settings, require_login, verify_clients):
    """A HEAD to the client endpoint should return just the client's version and checksum, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.head(CLIENT_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients)

    if response.status_code == 200:
        assert response[views.CLIENT_VERSION_HEADER] == tests_deb.CLIENT_VERSION
        assert response[views.CLIENT_CHECKSUM_HEADER] == tests_deb.CLIENT_CHECKSUM_DUMMY_2
    else:
        assert views.CLIENT_VERSION_HEADER not in response
        assert views.CLIENT_CHECKSUM_HEADER not in response

    assert response.content.decode('utf-8') == ''


def test_client_view_function():
    """Resolving the URL for the client endpoint should return the correct view."""
    view = resolve(CLIENT_URL)
    assert view.func is views.client


@patch('debmonitor.get_client', side_effect=RuntimeError)
def test_client_raise(mocked_get_client, client):
    """A GET to the client endpoint in case of error should return a text/plain 500."""
    response = client.get(CLIENT_URL)

    assert response.status_code == 500
    assert 'Unable to retrieve client code' in response.content.decode('utf-8')
    assert response['Content-Type'] == 'text/plain'
    assert mocked_get_client.called_once_with()


@patch('builtins.open', mock_open(read_data=tests_deb.CLIENT_BODY_DUMMY_1))
def test_client_get_auth(client, settings):
    """A GET to the client endpoint should return the client with its version and checksum, if authenticated."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    headers = {SSL_CLIENT_VERIFY_HEADER: SSL_CLIENT_VERIFY_SUCCESS}
    response = client.get(CLIENT_URL, **headers)

    assert response.status_code == 200
    assert response[views.CLIENT_VERSION_HEADER] == tests_deb.CLIENT_VERSION
    assert response[views.CLIENT_CHECKSUM_HEADER] == tests_deb.CLIENT_CHECKSUM_DUMMY_1
    assert response.content.decode('utf-8') == tests_deb.CLIENT_BODY_DUMMY_1


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
