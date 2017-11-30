import uuid

import pytest

from django.utils.text import slugify

from hosts import models


pytestmark = pytest.mark.django_db


def test_host_str():
    """The string representation of an Host object should return its name."""
    host = models.Host.objects.get(name='host1.example.com')
    assert str(host) == 'host1.example.com'


def test_hostpackage_str():
    """The string representation of an HostPackage object should return its host, package and versions details."""
    upgrade = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package1')
    upgrade_str = str(upgrade)
    assert 'host1.example.com' in upgrade_str
    assert 'package1' in upgrade_str
    assert '1.0.0-1' in upgrade_str
    assert '1.0.0-2' in upgrade_str


def test_hostpackage_str_no_upgrade():
    """The string representation of an HostPackage object should return its host, package and versions details."""
    upgrade = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package3')
    upgrade_str = str(upgrade)
    assert 'host1.example.com' in upgrade_str
    assert 'package3' in upgrade_str
    assert '3.0.0-1' in upgrade_str
    assert ' -' in upgrade_str


def test_host_save_kernel_slug():
    """Saving a new host should automatically populate the running_kernel_slug field."""
    os = models.OS.objects.get(name='os1')
    kernel = 'Running Kernel 1.0.0-1'
    host = models.Host(name=str(uuid.uuid4()), os=os, running_kernel=kernel)
    host.save()
    assert host.running_kernel_slug == slugify(kernel)


def test_disable_check_e003():
    """Ensure that Django check E003 for multiple ManyToManyField to the same model is disabled."""
    assert models.Host._check_m2m_through_same_relationship() == []
