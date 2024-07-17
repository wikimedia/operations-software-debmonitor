import uuid

import pytest

from django.core.exceptions import ValidationError

from src_packages import models


pytestmark = pytest.mark.django_db


def test_os_str():
    """The string representation of an OS object should return its name."""
    os = models.OS.objects.get(name='Debian 11')
    assert str(os) == 'Debian 11'


@pytest.mark.parametrize('name', (
    'Ubuntu',
    'Debian',
    'Debian 12',
    'Ubuntu 22.04'
))
def test_os_validation_ok(name):
    os = models.OS(name=name)
    os.clean_fields()


@pytest.mark.parametrize('name', (
    'Ubuntu 1',
    'Debian12',
    'Debian 111',
    'Ubuntu 22.04.01'
))
def test_os_validation_ko(name):
    os = models.OS(name=name)
    with pytest.raises(ValidationError, match='The OS name needs to follow'):
        os.clean_fields()


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
    assert 'Debian 11' in package_str


def test_srcpackageversion_get_or_create():
    """Calling the get_or_create() method of SrcPackageVersion should lazily create any missing intermediate object."""
    package_name = str(uuid.uuid4())
    os = models.OS.objects.get(name='Debian 11')
    package, created = models.SrcPackageVersion.objects.get_or_create(name=package_name, version='1.2.3-1', os=os)
    assert created
    assert isinstance(package.src_package, models.SrcPackage)


def test_srcpackageversion_get_or_create_cached():
    """Calling the get_or_create() method of SrcPackageVersion should use already queried objects, if available."""
    os = models.OS.objects.get(name='Debian 11')
    existing = models.SrcPackage.objects.get(name='package1')
    package, created = models.SrcPackageVersion.objects.get_or_create(
        name=existing.name, version='1.2.3-1', os=os, src_package=existing)
    assert created
    assert isinstance(package.src_package, models.SrcPackage)
    assert package.src_package is existing
