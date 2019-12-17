import pytest

from django.urls import resolve, reverse

from kernels import views
from tests.conftest import setup_auth_settings, validate_status_code


INDEX_URL = '/kernels/'
EXISTING_KERNEL_URL = INDEX_URL + '1_os1-100-1'  # Kernel slug
MISSING_KERNEL_URL = INDEX_URL + '99_os1-non_existing_kernel'


def test_index_reverse_url():
    """Reversing the kernels index page URL name should return the correct URL."""
    url = reverse('kernels:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client, settings, require_login, verify_clients):
    """Requesting the kernels index page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(INDEX_URL)
    validate_status_code(response, require_login)


def test_index_view_function():
    """Resolving the URL for the kernels index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.index


def test_detail_reverse_url_existing():
    """Reversing an existing kernel detail page URL name should return the correct URL."""
    url = reverse('kernels:detail', kwargs={'os_id': '1', 'slug': 'os1-100-1'})
    assert url == EXISTING_KERNEL_URL


def test_detail_reverse_url_missing():
    """Reversing a missing kernel detail page URL name should return the correct URL."""
    url = reverse('kernels:detail', kwargs={'os_id': '99', 'slug': 'os1-non_existing_kernel'})
    assert url == MISSING_KERNEL_URL


@pytest.mark.django_db
def test_detail_status_code_existing(client, settings, require_login, verify_clients):
    """Requesting an existing kernel detail page should return a 200 OK, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(EXISTING_KERNEL_URL)
    validate_status_code(response, require_login)


@pytest.mark.django_db
def test_detail_status_code_missing(client, settings, require_login, verify_clients):
    """Requesting a missing kernel detail page should return a 404 NOT FOUND, if authenticated."""
    setup_auth_settings(settings, require_login, verify_clients)
    response = client.get(MISSING_KERNEL_URL)
    validate_status_code(response, require_login, default=404)


def test_detail_view_function():
    """Resolving the URL for the kernel detail page should return the correct view."""
    view = resolve(EXISTING_KERNEL_URL)
    assert view.func is views.detail
