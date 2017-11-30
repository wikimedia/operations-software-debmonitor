import uuid

import pytest

from src_packages import models


pytestmark = pytest.mark.django_db


def test_os_str():
    """The string representation of an OS object should return its name."""
    os = models.OS.objects.get(name='os1')
    assert str(os) == 'os1'


def test_srcpackage_str():
    """The string representation of a SrcPackage object should return its name."""
    package = models.SrcPackage.objects.get(name='package1')
    assert str(package) == 'package1'


def test_srcpackageversion_str():
    """The string representation of a SrcPackageVersion object should return its name, version and OS."""
    package = models.SrcPackageVersion.objects.get(src_package__name='package1', version='1.0.0-1')
    package_str = str(package)
    assert 'package1' in package_str
    assert '1.0.0-1' in package_str
    assert 'os1' in package_str


def test_srcpackageversion_get_or_create():
    """Calling the get_or_create() method of SrcPackageVersion should lazily create any missing intermediate object."""
    package_name = str(uuid.uuid4())
    os = models.OS.objects.get(name='os1')
    package, created = models.SrcPackageVersion.objects.get_or_create(name=package_name, version='1.2.3-1', os=os)
    assert created
    assert isinstance(package.src_package, models.SrcPackage)
