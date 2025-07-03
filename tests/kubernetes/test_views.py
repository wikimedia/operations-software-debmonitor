import pytest

from unittest.mock import patch

from django.urls import resolve, reverse

from debmonitor.middleware import APPLICATION_JSON
from kubernetes import views
from tests.conftest import setup_auth_settings, validate_status_code


INDEX_URL = '/kubernetes/'
UPDATE_URL = f'{INDEX_URL}update'
PAYLOAD_UPDATE_EXISTING_OK = """{
    "cluster": "ClusterA",
    "images": {
        "registry.example.com/component/image-deployed:1.2.3-1": {
            "NamespaceA": 3
        }
    }
}
"""
PAYLOAD_UPDATE_NEW_OK = """{
    "cluster": "ClusterB",
    "images": {
        "registry.example.com/component/image-deployed:1.2.3-1": {
            "NamespaceB": 1
        }
    }
}
"""
PAYLOAD_UPDATE_MISSING_IMAGE = """{
    "cluster": "ClusterB",
    "images": {
    "registry.example.com/component/image-missing:1.2.3-1": {
            "NamespaceB": 1
        }
    }
}
"""
PAYLOAD_UPDATE_VALUE_ERROR = """{
    "cluster": "ClusterB",
    "images": {
        "registry.example.com/component/image-deployed:1.2.3-1": {
            "NamespaceB": "invalid"
        }
    }
}
"""


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


def test_update_reverse_url_existing():
    """Reversing the update URL name should return the correct URL."""
    url = reverse('kubernetes:update')
    assert url == UPDATE_URL


def test_update_view_function():
    """Resolving the URL for the update page should return the correct view."""
    view = resolve(UPDATE_URL)
    assert view.func is views.update_kubernetes_images


def test_update_no_post(client, settings, require_login, verify_clients):
    """Trying to call update without a POST content should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', UPDATE_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_invalid_payload(client, settings, require_login, verify_clients):
    """Trying to call update with an invalid JSON payload should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', UPDATE_URL, 'invalid_json')
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


@pytest.mark.parametrize('payload', (
    '{"images": {}}',
    '{"cluster": "ClusterA", "images": []}',
))
def test_update_bad_paylod(client, settings, require_login, verify_clients, payload):
    """Trying to call update with a payload missing some parts should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', UPDATE_URL, payload)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


@pytest.mark.django_db
def test_update_existing_ok(client):
    """Updating an existing Kubernetes image with a correct payload should return 201 Created."""
    response = client.generic('POST', UPDATE_URL, PAYLOAD_UPDATE_EXISTING_OK)
    assert views.KubernetesImage.objects.get(pk=1).containers == 3
    assert response.status_code == 201
    assert response['Content-Type'] == APPLICATION_JSON
    response_data = response.json()
    assert response_data['success']
    assert response_data['missing'] == []
    assert response_data['errors'] == []


@pytest.mark.django_db
def test_update_new_ok(client):
    """Updating with a new Kubernetes image with a correct payload should return 201 Created."""
    response = client.generic('POST', UPDATE_URL, PAYLOAD_UPDATE_NEW_OK)
    kub_image = views.KubernetesImage.objects.last()
    assert response.status_code == 201
    assert response['Content-Type'] == APPLICATION_JSON
    response_data = response.json()
    assert response_data['success']
    assert response_data['missing'] == []
    assert response_data['errors'] == []
    assert kub_image.cluster == 'ClusterB'
    assert kub_image.namespace == 'NamespaceB'
    assert kub_image.image.name == 'registry.example.com/component/image-deployed:1.2.3-1'
    assert kub_image.containers == 1


@pytest.mark.django_db
def test_update_key_error(client):
    """Updating with a payload missing some keys should skip that image and return the error."""
    response = client.generic('POST', UPDATE_URL, PAYLOAD_UPDATE_VALUE_ERROR)
    assert response.status_code == 202
    assert response['Content-Type'] == APPLICATION_JSON
    response_data = response.json()
    assert not response_data['success']
    assert len(response_data['errors']) == 1
    assert not response_data['missing']
    error = response_data['errors'][0]
    assert error['image'] == 'registry.example.com/component/image-deployed:1.2.3-1'
    assert error['cluster'] == 'ClusterB'
    assert error['namespace'] == 'NamespaceB'
    assert error['error'] == "Field 'containers' expected a number but got 'invalid'."


@pytest.mark.django_db
def test_update_missing_image(client):
    """Updating with a payload referring to an image missing from Debmonitor should skip that image."""
    response = client.generic('POST', UPDATE_URL, PAYLOAD_UPDATE_MISSING_IMAGE)
    assert response.status_code == 202
    assert response['Content-Type'] == APPLICATION_JSON
    response_data = response.json()
    assert not response_data['success']
    assert len(response_data['missing']) == 1
    assert not response_data['errors']
    assert response_data['missing'] == ['registry.example.com/component/image-missing:1.2.3-1']


@pytest.mark.django_db
@patch('kubernetes.views._update_v1', side_effect=RuntimeError('error'))
def test_update_raise(mocked_update_v1, client):
    """If the update raise an exception, a plain/text 500 should be returned."""
    response = client.generic('POST', UPDATE_URL, PAYLOAD_UPDATE_EXISTING_OK)
    assert response.status_code == 500
    assert 'Unable to update Kubernetes images for cluster ClusterA: error' in response.content.decode('utf-8')
    assert response['Content-Type'] == 'text/plain'
    assert mocked_update_v1.called
