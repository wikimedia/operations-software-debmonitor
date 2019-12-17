import uuid

from unittest.mock import patch

import pytest

from django.urls import resolve, reverse

# from debmonitor import middleware
from images import views
from images.models import Image, ImagePackage
from tests.conftest import IMAGENAME, setup_auth_settings, validate_status_code


INDEX_URL = '/images/'
EXISTING_IMAGE_URL = INDEX_URL + IMAGENAME
EXISTING_IMAGE_UPDATE_URL = EXISTING_IMAGE_URL + '/update'
MISSING_IMAGE_URL = INDEX_URL + 'non_existing_image_example'
PAYLOAD_NEW_OK = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "os1",
    "image_name": "%(uuid)s",
    "installed": [
        {"name": "pkg1-%(uuid)s", "version": "1.0.0-1", "source": "pkg1-%(uuid)s"},
        {"name": "pkg2-%(uuid)s", "version": "1.0.0-1", "source": "pkg2-%(uuid)s"},
        {"name": "pkg3-%(uuid)s", "version": "1.0.0-1", "source": "pkg3-%(uuid)s"}
    ]
}"""
PAYLOAD_EXISTING_NO_UPDATE = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "os1",
    "image_name": "parsoid",
    "installed": [
        {"name": "package1", "version": "1.0.0-1", "source": "package1"},
        {"name": "package2", "version": "2.0.0-1", "source": "package2"}
    ]
}"""
PAYLOAD_EXISTING_UPDATE = """{
    "api_version": "v1",
    "update_type": "full",
    "os": "os1",
    "image_name": "parsoid",
    "installed": [
        {"name": "package1", "version": "1.0.0-1", "source": "package1"},
        {"name": "package2", "version": "2.0.0-2", "source": "package2"},
        {"name": "pkg1-%(uuid)s", "version": "1.0.0-1", "source": "pkg1-%(uuid)s"}
    ]
}"""
PAYLOAD_NEW_BROKEN = """{
    "os": "os1",
    "image_name": "%(uuid)s"
}"""
PAYLOAD_UPGRADABLE = """{
    "api_version": "v1",
    "update_type": "upgradable",
    "os": "os1",
    "image_name": "parsoid",
    "upgradable": [
        {"name": "package1", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "package1", "type": ""},
        {"name": "pkg3-%(uuid)s", "version_from": "1.0.0-1", "version_to": "1.0.0-2", "source": "pkg3-%(uuid)s",
         "type": ""}
    ]
}"""


def test_index_reverse_url():
    """Reversing the images index page URL name should return the correct URL."""
    url = reverse('images:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the images index page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the images index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_detail_reverse_url_existing():
    """Reversing an existing image detail page URL name should return the correct URL."""
    url = reverse('images:detail', kwargs={'name': 'parsoid'})
    assert url == EXISTING_IMAGE_URL


def test_detail_reverse_url_missing():
    """Reversing a missing image detail page URL name should return the correct URL."""
    url = reverse('images:detail', kwargs={'name': 'non_existing_image_example'})
    assert url == MISSING_IMAGE_URL


@pytest.mark.django_db
def test_detail_status_code_existing(client, settings, require_login, verify_clients):
    """Requesting an existing image detail page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(EXISTING_IMAGE_URL)
    validate_status_code(response, require_login)


@pytest.mark.django_db
def test_detail_status_code_missing(client, settings, require_login, verify_clients):
    """Requesting a missing image detail page should return a 404 NOT FOUND, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(MISSING_IMAGE_URL)
    validate_status_code(response, require_login, default=404)


@pytest.mark.django_db
def test_detail_delete_status_code_existing(client, settings, require_login, verify_clients):
    """Deleting an existing image should return a 204 No Content, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    image = Image.objects.get(name=IMAGENAME)
    image_packages = ImagePackage.objects.filter(image=image)
    assert image is not None
    assert len(image_packages) > 0

    response = client.delete(EXISTING_IMAGE_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=204)

    if response.status_code == 204:  # The image and all its packages were deleted
        assert len(ImagePackage.objects.filter(image=image.id)) == 0
        with pytest.raises(Image.DoesNotExist, match='Image matching query does not exist'):
            Image.objects.get(name=IMAGENAME)
    else:  # Nothing was changed
        assert image == Image.objects.get(name=IMAGENAME)
        assert list(image_packages) == list(ImagePackage.objects.filter(image=image))
        if response.status_code == 403:
            assert 'Client certificate validation failed' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_detail_delete_status_code_missing(client, settings, require_login, verify_clients):
    """Trying to delete a missing image should return a 404 Not Found, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.delete(MISSING_IMAGE_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=404)


def test_update_reverse_url_existing():
    """Reversing an existing image update URL name should return the correct URL."""
    url = reverse('images:update', kwargs={'name': 'parsoid'})
    assert url == EXISTING_IMAGE_UPDATE_URL


def test_update_view_function():
    """Resolving the URL for the image update page should return the correct view."""
    view = resolve(EXISTING_IMAGE_UPDATE_URL)
    assert view.func is views.update_image


def test_update_status_code_no_post(client, settings, require_login, verify_clients):
    """Trying to update an image without a POST content should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL)
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_status_code_invalid_payload(client, settings, require_login, verify_clients):
    """Trying to update an image with an invalid JSON payload should return 400 Bad Request, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL, 'invalid_json')
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


def test_update_status_code_wrong_imagename(client, settings, require_login, verify_clients):
    """Trying to update an image with a payload for a different image should return 400 Bad Request,
    if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL,
                              '{"image_name": "non_existing_image_example", "os": "os1"}')
    validate_status_code(response, require_login, verify_clients=verify_clients, default=400)


@pytest.mark.django_db
def test_update_status_code_invalid_os(client):
    """Trying to update an image with a payload with an invalid OS should return 400 Bad Request."""
    response = client.generic(
        'POST', EXISTING_IMAGE_UPDATE_URL, '{"image_name": "parsoid", "os": "invalid_os"}')
    assert response.status_code == 400


@pytest.mark.django_db
def test_update_status_code_new_image_ok(client):
    """Updating a non existing image with a correct payload should return 201 Created."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', '/images/{uuid}/update'.format(uuid=rand), PAYLOAD_NEW_OK % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_new_image_ko(client):
    """Updating a non existing image with an incorrect payload should return 400 Bad Request."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', '/images/{uuid}/update'.format(uuid=rand), PAYLOAD_NEW_BROKEN % {'uuid': rand})
    assert response.status_code == 400


@pytest.mark.django_db
def test_update_status_code_existing_no_update(client):
    """Updating an existing image with a correct payload with no update should return 201 Created."""
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL, PAYLOAD_EXISTING_NO_UPDATE)
    assert response.status_code == 201


@pytest.mark.django_db
def test_update_status_code_existing_update(client):
    """Updating an existing image with a correct payload with updates should return 201 Created."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL, PAYLOAD_EXISTING_UPDATE % {'uuid': rand})
    assert response.status_code == 201


@pytest.mark.django_db
@patch('images.views._update_v1', side_effect=RuntimeError)
def test_update_raise(mocked_update_v1, client):
    """If the update raise an exception, a plain/text 500 should be returned."""
    rand = str(uuid.uuid4())
    response = client.generic('POST', EXISTING_IMAGE_UPDATE_URL, PAYLOAD_EXISTING_UPDATE % {'uuid': rand})
    assert response.status_code == 500
    assert 'Unable to update image' in response.content.decode('utf-8')
    assert response['Content-Type'] == 'text/plain'
    assert mocked_update_v1.called
