import pytest

from django.urls import reverse
from django.urls import resolve

from hosts import views


INDEX_URL = '/kernels/'
EXISTING_KERNEL_URL = INDEX_URL + 'os1-100-1'  # Kernel slug
MISSING_KERNEL_URL = INDEX_URL + 'os1-non_existing_kernel'


def test_index_reverse_url():
    """Reversing the kernels index page URL name should return the correct URL."""
    url = reverse('kernels:index')
    assert url == INDEX_URL


@pytest.mark.django_db
def test_index_status_code(client):
    """Requesting the kernels index page should return a 200 OK."""
    response = client.get(INDEX_URL)
    assert response.status_code == 200


def test_index_view_function():
    """Resolving the URL for the kernels index page should return the correct view."""
    view = resolve(INDEX_URL)
    assert view.func is views.kernel_index


def test_detail_reverse_url_existing():
    """Reversing an existing kernel detail page URL name should return the correct URL."""
    url = reverse('kernels:detail', kwargs={'slug': 'os1-100-1'})
    assert url == EXISTING_KERNEL_URL


def test_detail_reverse_url_missing():
    """Reversing a missing kernel detail page URL name should return the correct URL."""
    url = reverse('kernels:detail', kwargs={'slug': 'os1-non_existing_kernel'})
    assert url == MISSING_KERNEL_URL


@pytest.mark.django_db
def test_detail_status_code_existing(client):
    """Requesting an existing kernel detail page should return a 200 OK."""
    response = client.get(EXISTING_KERNEL_URL)
    assert response.status_code == 200


@pytest.mark.django_db
def test_detail_status_code_missing(client):
    """Requesting a missing kernel detail page should return a 404 NOT FOUND."""
    response = client.get(MISSING_KERNEL_URL)
    assert response.status_code == 404


def test_detail_view_function():
    """Resolving the URL for the kernel detail page should return the correct view."""
    view = resolve(EXISTING_KERNEL_URL)
    assert view.func is views.kernel_detail
