import pytest

from django.urls import resolve, reverse

from src_packages import views
from tests.conftest import setup_auth_settings, validate_status_code


INDEX_URL = '/source-packages/'
EXISTING_PACKAGE_URL = INDEX_URL + 'package1'
MISSING_PACKAGE_URL = INDEX_URL + 'non_existing_package'


def test_index_reverse_url():
    """Reversing the source packages index page URL name should return the correct URL."""
    url = reverse('src_packages:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the source packages index page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the source packages index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_detail_reverse_url_existing():
    """Reversing an existing source package detail page URL name should return the correct URL."""
    url = reverse('src_packages:detail', kwargs={'name': 'package1'})
    assert url == EXISTING_PACKAGE_URL


def test_detail_reverse_url_missing():
    """Reversing a missing source package detail page URL name should return the correct URL."""
    url = reverse('src_packages:detail', kwargs={'name': 'non_existing_package'})
    assert url == MISSING_PACKAGE_URL


@pytest.mark.django_db
def test_detail_status_code_existing(client, settings, require_login, verify_clients):
    """Requesting an existing source package detail page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(EXISTING_PACKAGE_URL)
    validate_status_code(response, require_login)


@pytest.mark.django_db
def test_detail_status_code_missing(client, settings, require_login, verify_clients):
    """Requesting a missing source package detail page should return a 404 NOT FOUND, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(MISSING_PACKAGE_URL)
    validate_status_code(response, require_login, default=404)


def test_detail_view_function():
    """Resolving the URL for the source package detail page should return the correct view."""
    view = resolve(EXISTING_PACKAGE_URL)
    assert view.func is views.detail
