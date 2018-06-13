from unittest.mock import patch, mock_open

import pytest

from django.urls import resolve, reverse

from debmonitor import views
from hosts import SSL_CLIENT_VERIFY_HEADER, SSL_CLIENT_VERIFY_SUCCESS


INDEX_URL = '/'
CLIENT_URL = '/client'
CLIENT_VERSION = '0.1.2'
CLIENT_CHECKSUM_DUMMY_1 = 'bc45bcc2f37b13995fa4d7ae82cecd6e'
CLIENT_CHECKSUM_DUMMY_2 = '8b832267d01acf421e0a8aaed7b02864'
CLIENT_BODY_DUMMY_1 = """import os
__version__ = '0.1.2'
"""
CLIENT_BODY_DUMMY_2 = """import os
__dummy__ = 1
__version__ = '0.1.2'
"""
CLIENT_BODY_NO_VERSION = 'import os'
CLIENT_CHECKSUM_NO_VERSION = 'ed9f4b8f879ddbb59fda1057ea3a2810'


def test_index_reverse_url():
    """Reversing the homepage URL name should return the correct URL."""
    url = reverse('index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client):
    """Requesting the homepage should return a 200 OK."""
    response = client.get(INDEX_URL)
    assert response.status_code == 200


def test_index_view_function():
    """Resolving the URL for the homepage should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_client_reverse_url():
    """Reversing the client URL name should return the correct URL."""
    url = reverse('client')
    assert url == CLIENT_URL


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_NO_VERSION))
def test_client_get_no_version(client):
    """A GET to the client endpoint should return the client with its version and checksum."""
    response = client.get(CLIENT_URL)

    assert response.status_code == 200
    assert response[views.CLIENT_VERSION_HEADER] == ''
    assert response[views.CLIENT_CHECKSUM_HEADER] == CLIENT_CHECKSUM_NO_VERSION
    assert response.content.decode('utf-8') == CLIENT_BODY_NO_VERSION


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_DUMMY_1))
def test_client_get(client):
    """A GET to the client endpoint should return the client with its version and checksum."""
    response = client.get(CLIENT_URL)

    assert response.status_code == 200
    assert response[views.CLIENT_VERSION_HEADER] == CLIENT_VERSION
    assert response[views.CLIENT_CHECKSUM_HEADER] == CLIENT_CHECKSUM_DUMMY_1
    assert response.content.decode('utf-8') == CLIENT_BODY_DUMMY_1


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_DUMMY_2))
def test_client_head(client):
    """A HEAD to the client endpoint should return the client's version and checksum."""
    response = client.head(CLIENT_URL)

    assert response.status_code == 200
    assert response[views.CLIENT_VERSION_HEADER] == CLIENT_VERSION
    assert response[views.CLIENT_CHECKSUM_HEADER] == CLIENT_CHECKSUM_DUMMY_2
    assert response.content.decode('utf-8') == ''


def test_client_view_function():
    """Resolving the URL for the client endpoint should return the correct view."""
    view = resolve(CLIENT_URL)
    assert view.func is views.client


def test_client_no_auth(client, settings):
    """A GET to the client endpoint without auth should return Forbidden."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    response = client.get(CLIENT_URL)

    assert response.status_code == 403
    assert views.CLIENT_VERSION_HEADER not in response
    assert views.CLIENT_CHECKSUM_HEADER not in response
    assert 'Client certificate validation failed' in response.content.decode('utf-8')


@patch('builtins.open', mock_open(read_data=CLIENT_BODY_DUMMY_1))
def test_client_auth(client, settings):
    """A GET to the client endpoint with auth should return the client code."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    headers = {SSL_CLIENT_VERIFY_HEADER: SSL_CLIENT_VERIFY_SUCCESS}
    response = client.get(CLIENT_URL, **headers)

    assert response.status_code == 200
    assert response[views.CLIENT_VERSION_HEADER] == CLIENT_VERSION
    assert response[views.CLIENT_CHECKSUM_HEADER] == CLIENT_CHECKSUM_DUMMY_1
    assert response.content.decode('utf-8') == CLIENT_BODY_DUMMY_1


@patch('debmonitor.get_client', side_effect=RuntimeError)
def test_client_raise(mocked_get_client, client):
    """A GET to the client endpoint in case of error should return a text/plain 500."""
    response = client.get(CLIENT_URL)

    assert response.status_code == 500
    assert 'Unable to retrieve client code' in response.content.decode('utf-8')
    assert response['Content-Type'] == 'text/plain'
    assert mocked_get_client.called_once_with()
