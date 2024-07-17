import uuid

import pytest

from django.core.exceptions import ValidationError

from bin_packages import models
from src_packages.models import OS, SrcPackageVersion


pytestmark = pytest.mark.django_db


def test_package_str():
    """The string representation of a Package object should return its name."""
    package = models.Package.objects.get(name='package1')
    assert str(package) == 'package1'


def test_packageversion_str():
    """The string representation of a PackageVersion object should return its name, version and OS."""
    package = models.PackageVersion.objects.get(package__name='package1', version='1.0.0-1')
    package_str = str(package)
    assert 'package1' in package_str
    assert '1.0.0-1' in package_str
    assert 'Debian 11' in package_str


def test_packageversion_get_or_create():
    """Calling the get_or_create() method of PackageVersion should lazily create any missing intermediate object."""
    package_name = str(uuid.uuid4())
    os = OS.objects.get(name='Debian 11')
    package, created = models.PackageVersion.objects.get_or_create(
        name=package_name, version='1.2.3-1', source=package_name, os=os)
    assert created
    assert isinstance(package.package, models.Package)
    assert isinstance(package.src_package_version, SrcPackageVersion)


def test_packageversion_clean():
    """Calling save() with some invalida data should raise ValidationError."""
    package_name = str(uuid.uuid4())
    os1 = OS.objects.get(name='Debian 11')
    os2 = OS.objects.get(name='Ubuntu 24.04')
    package, created = models.PackageVersion.objects.get_or_create(
        name=package_name, version='1.2.3-1', source=package_name, os=os1)
    assert created
    package.os = os2

    with pytest.raises(ValidationError, match='OS mismatch between'):
        package.save()
