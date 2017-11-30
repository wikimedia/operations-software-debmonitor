import pytest

from django.urls import reverse
from django.urls import resolve

from debmonitor import views


INDEX_URL = '/'


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
