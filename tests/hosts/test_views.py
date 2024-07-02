import uuid

from unittest.mock import patch

import pytest

from django.urls import resolve, reverse

from debmonitor import middleware
from hosts import views
from hosts.models import Host, HostPackage
from tests.conftest import HOSTNAME, setup_auth_settings, validate_status_code


INDEX_URL = '/hosts/'
EXISTING_HOST_URL = INDEX_URL + HOSTNAME
EXISTING_HOST_UPDATE_URL = EXISTING_HOST_URL + '/update'
MISSING_HOST_URL = INDEX_URL + 'non_existing_host.example.com'
PAYLOAD_NEW_OK = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "Debian 13",
    "hostname": "%(uuid)s",
    "running_kernel": {
        "version": "%(uuid)s",
        "version": "kernel_%(uuid)s"
    },
    "installed": [
        {"name": "pkg1-%(uuid)s", "version": "1.0.0-1", "source": "pkg1-%(uuid)s"},
        {"name": "pkg2-%(uuid)s", "version": "1.0.0-1", "source": "pkg2-%(uuid)s"},
        {"name": "pkg3-%(uuid)s", "version": "1.0.0-1", "source": "pkg3-%(uuid)s"}
    ],
    "uninstalled": [
        {"name": "pkg3-%(uuid)s", "version": "1.0.0-1", "source": "pkg3-%(uuid)s"}
    ],
    "upgradable": [
        {"name": "pkg1-%(uuid)s", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "pkg1-%(uuid)s",
         "type": ""}
    ]
}"""
PAYLOAD_EXISTING_NO_UPDATE = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "Debian 11",
    "hostname": "host1.example.com",
    "running_kernel": {
        "version": "100",
        "version": "os1-100-1"
    },
    "installed": [
        {"name": "package1", "version": "1.0.0-1", "source": "package1"},
        {"name": "package2", "version": "2.0.0-1", "source": "package2"}
    ]
}"""
PAYLOAD_EXISTING_UPDATE = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "Debian 11",
    "hostname": "host1.example.com",
    "running_kernel": {
        "version": "100",
        "version": "os1-100-2"
    },
    "installed": [
        {"name": "package1", "version": "1.0.0-1", "source": "package1"},
        {"name": "package2", "version": "2.0.0-2", "source": "package2"},
        {"name": "pkg1-%(uuid)s", "version": "1.0.0-1", "source": "pkg1-%(uuid)s"}
    ],
    "uninstalled": [
        {"name": "pkg2-%(uuid)s", "version": "2.0.0-1", "source": "pkg2-%(uuid)s"}
    ],
    "upgradable": [
        {"name": "package1", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "package1", "type": ""},
        {"name": "pkg3-%(uuid)s", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "pkg3-%(uuid)s",
         "type": ""}
    ]
}"""
PAYLOAD_NEW_KO = """{
    "os": "Debian 11",
    "hostname": "%(uuid)s"
}"""
PAYLOAD_UPGRADABLE = """{
    "api_version": "v1",
    "update_type": "upgradable",
    "os": "Debian 11",
    "hostname": "host1.example.com",
    "running_kernel": {
        "version": "100",
        "version": "os1-100-2"
    },
    "upgradable": [
        {"name": "package1", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "package1", "type": ""},
        {"name": "pkg3-%(uuid)s", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "pkg3-%(uuid)s",
         "type": ""}
    ]
}"""


def test_index_reverse_url():
    """Reversing the hosts index page URL name should return the correct URL."""
    url = reverse('hosts:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the hosts index page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the hosts index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_detail_reverse_url_existing():
    """Reversing an existing host detail page URL name should return the correct URL."""
    url = reverse('hosts:detail', kwargs={'name': HOSTNAME})
    assert url == EXISTING_HOST_URL


def test_detail_reverse_url_missing():
    """Reversing a missing host detail page URL name should return the correct URL."""
    url = reverse('hosts:detail', kwargs={'name': 'non_existing_host.example.com'})
    assert url == MISSING_HOST_URL


@pytest.mark.django_db
def test_detail_status_code_existing(client, settings, require_login, verify_clients):
    """Requesting an existing host detail page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(EXISTING_HOST_URL)
    validate_status_code(response, require_login)


@pytest.mark.django_db
def test_detail_status_code_missing(client, settings, require_login, verify_clients):
    """Requesting a missing host detail page should return a 404 NOT FOUND, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(MISSING_HOST_URL)
    validate_status_code(response, require_login, default=404)


@pytest.mark.django_db
def test_detail_delete_status_code_existing(client, settings, require_login, verify_clients):
    """Deleting an existing host should return a 204 No Content, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    # Get an existing host and its packages
    host = Host.objects.get(name=HOSTNAME)
    host_packages = HostPackage.objects.filter(host=host)
    assert host is not None
    assert len(host_packages) > 0

    response = client.delete(EXISTING_HOST_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=204)

    if response.status_code == 204:  # The host and all its packages were deleted
        assert len(HostPackage.objects.filter(host=host.id)) == 0
        with pytest.raises(Host.DoesNotExist, match='Host matching query does not exist'):
            Host.objects.get(name=HOSTNAME)
    else:  # Nothing was changed
        assert host == Host.objects.get(name=HOSTNAME)
        assert list(host_packages) == list(HostPackage.objects.filter(host=host))
        if response.status_code == 403:
            assert 'Client certificate validation failed' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_detail_delete_status_code_missing(client, settings, require_login, verify_clients):
    """Trying to delete a missing host should return a 404 Not Found, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.delete(MISSING_HOST_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=404)


def test_update_reverse_url_existing():
    """Reversing an existing host update URL name should return the correct URL."""
    url = reverse('hosts:update', kwargs={'name': 'host1.example.com'})
    assert url == EXISTING_HOST_UPDATE_URL


def test_update_view_function():
    """Resolving the URL for the host update page should return the correct view."""
    view = resolve(EXISTING_HOST_UPDATE_URL)
    assert view.func is views.update


def test_update_status_code_no_post(client, settings, require_login, verify_clients):
    """Trying to update an host without a POST content should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_status_code_invalid_payload(client, settings, require_login, verify_clients):
    """Trying to update an host with an invalid JSON payload should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, 'invalid_json')
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_status_code_wrong_hostname(client, settings, require_login, verify_clients):
    """Trying to update an host with a payload for a different host should return 400 Bad Reques, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, '{"hostname": "non_existing_host.example.com"}')
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_status_code_missing_cert(client, settings):
    """Trying to update an host with a missing certificate should return 403 Forbidden."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE)
    assert response.status_code == 403


def test_update_status_code_invalid_cert(client, settings):
    """Trying to update an host with an invalid wrong should return 403 Forbidden."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    extra = {middleware.SSL_CLIENT_VERIFY_HEADER: 'FAILED:reason'}
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE, **extra)
    assert response.status_code == 403
    assert 'Client certificate validation failed' in response.content.decode('utf-8')


def test_update_status_code_wrong_cert(client, settings):
    """Trying to update an host with a valid wrong certificate should return 403 Forbidden."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    extra = {middleware.SSL_CLIENT_VERIFY_HEADER: 'SUCCESS',
             middleware.SSL_CLIENT_SUBJECT_DN_HEADER: 'CN=host2.example.com'}
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE, **extra)
    assert response.status_code == 403
    assert 'Unauthorized to modify host' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_update_status_code_cert_ok(client, settings):
    """Trying to update an host with a valid certificate for the correct host should return 201 Created."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    extra = {middleware.SSL_CLIENT_VERIFY_HEADER: 'SUCCESS',
             middleware.SSL_CLIENT_SUBJECT_DN_HEADER: 'CN=host1.example.com'}
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE, **extra)
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_proxy_host(client, settings):
    """Trying to update an host with a valid certificate from an allowed proxy host should return 201 Created."""
    settings.DEBMONITOR_VERIFY_CLIENTS = True
    settings.DEBMONITOR_PROXY_HOSTS = ['host2.example.com']
    extra = {middleware.SSL_CLIENT_VERIFY_HEADER: 'SUCCESS',
             middleware.SSL_CLIENT_SUBJECT_DN_HEADER: 'CN=host2.example.com'}
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE, **extra)
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_invalid_os(client):
    """Trying to update an host with a payload with an invalid OS should return 400 Bad Request."""
    response = client.generic(
        'POST', EXISTING_HOST_UPDATE_URL, '{"hostname": "host1.example.com", "os": "invalid_os"}')
    assert response.status_code == 400


@pytest.mark.django_db
def test_update_status_code_new_host_ok(client):
    """Updating a non existing host with a correct payload should return 201 Created."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', '/hosts/{uuid}/update'.format(uuid=rand), PAYLOAD_NEW_OK % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_new_host_ko(client):
    """Updating a non existing host with an incorrect payload should return 400 Bad Request."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', '/hosts/{uuid}/update'.format(uuid=rand), PAYLOAD_NEW_KO % {'uuid': rand})
    assert response.status_code == 400


@pytest.mark.django_db
def test_update_status_code_existing_no_update(client):
    """Updating an existing host with a correct payload with no update should return 201 Created."""
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE)
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_existing_update(client):
    """Updating an existing host with a correct payload with updates should return 201 Created."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_UPDATE % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_upgradable(client):
    """Updating an existing host with a correct payload with upgradable updates should return 201 Created."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_UPGRADABLE % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_upgradable_updated(client):
    """Updating an existing host with a payload that an upgraded package is upgradable should return 201 Created."""
    rand = str(uuid.uuid4())
    payload = PAYLOAD_UPGRADABLE.replace(
        '"version_from": "1.0.0-1", "version_to": "1.0.0-2"', '"version_from": "1.0.0-0", "version_to": "1.0.0-1"')
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, payload % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_upgradable_client2(client):
    """Updating an existing host with a payload from CLI version 0.1client2 or earlier should return 201 Created."""
    rand = str(uuid.uuid4())
    payload = PAYLOAD_UPGRADABLE.replace('"update_type": "upgradable"', '"update_type": "partial"')
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, payload % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
@patch('hosts.views._update_v1', side_effect=RuntimeError)
def test_update_raise(mocked_update_v1, client):
    """If the update raise an exception, a plain/text 500 should be returned."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', EXISTING_HOST_UPDATE_URL, PAYLOAD_EXISTING_UPDATE % {'uuid': rand})
    assert response.status_code == 500
    assert 'Unable to update host' in response.content.decode('utf-8')
    assert response['Content-Type'] == 'text/plain'
    assert mocked_update_v1.called
