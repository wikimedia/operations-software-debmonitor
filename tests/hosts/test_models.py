import pytest

from django.core.exceptions import ValidationError

from bin_packages.models import Package
from hosts import models
from src_packages.models import OS

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


def test_disable_check_e003():
    """Ensure that Django check E003 for multiple ManyToManyField to the same model is disabled."""
    assert models.Host._check_m2m_through_same_relationship() == []


def test_packageversion_wrong_pkg_os():
    """Calling save() with a package version with a wrong OS should raise ValidationError."""
    os2 = OS.objects.get(name='Ubuntu 24.04')
    host_package = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package3')
    host_package.package_version.os = os2

    with pytest.raises(ValidationError, match='OS mismatch between'):
        host_package.save()


def test_packageversion_wrong_upgrade_os():
    """Calling save() with an upgradable package version with a wrong OS should raise ValidationError."""
    os2 = OS.objects.get(name='Ubuntu 24.04')
    host_package = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package1')
    host_package.upgradable_version.os = os2

    with pytest.raises(ValidationError, match='OS mismatch between'):
        host_package.save()


def test_packageversion_wrong_pkg():
    """Calling save() with a package version with a wrong package should raise ValidationError."""
    package = Package.objects.get(name='package1')
    host_package = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package3')
    host_package.package = package

    with pytest.raises(ValidationError, match='Package name mismatch'):
        host_package.save()


def test_packageversion_wrong_upgrade():
    """Calling save() with an upgradable package version with a wrong package should raise ValidationError."""
    package = Package.objects.get(name='package3')
    host_package = models.HostPackage.objects.get(host__name='host1.example.com', package__name='package1')
    host_package.upgradable_package = package

    with pytest.raises(ValidationError, match='Upgradable package name mismatch'):
        host_package.save()
