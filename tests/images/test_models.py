import pytest

from django.core.exceptions import ValidationError

from bin_packages.models import Package
from images import models
from src_packages.models import OS
from tests.conftest import IMAGENAME


pytestmark = pytest.mark.django_db


def test_image_str():
    """The string representation of an Image object should return its name."""
    image = models.Image.objects.get(name=IMAGENAME)
    assert str(image) == IMAGENAME


def test_imagepackage_str_no_upgrade():
    """The string representation of an ImagePackage object should return its image, package and versions details."""
    package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='gcc-9')
    package_str = str(package)
    assert IMAGENAME in package_str
    assert 'gcc-9' in package_str
    assert '9.0.0-1' in package_str
    assert ' -' in package_str


def test_imagepackage_str():
    """The string representation of an ImagePackage object should return its image, package and versions details."""
    package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='nodejs')
    package_str = str(package)
    assert IMAGENAME in package_str
    assert 'nodejs' in package_str
    assert '1.2.3-4' in package_str
    assert '1.2.3-5' in package_str


def test_disable_check_e003():
    """Ensure that Django check E003 for multiple ManyToManyField to the same model is disabled."""
    assert models.Image._check_m2m_through_same_relationship() == []


def test_packageversion_wrong_pkg_os():
    """Calling save() with a package version with a wrong OS should raise ValidationError."""
    os2 = OS.objects.get(name='Ubuntu 24.04')
    image_package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='nodejs')
    image_package.package_version.os = os2

    with pytest.raises(ValidationError, match='OS mismatch between'):
        image_package.save()


def test_packageversion_wrong_upgrade_os():
    """Calling save() with an upgradable package version with a wrong OS should raise ValidationError."""
    os2 = OS.objects.get(name='Ubuntu 24.04')
    image_package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='nodejs')
    image_package.upgradable_imageversion.os = os2

    with pytest.raises(ValidationError, match='OS mismatch between'):
        image_package.save()


def test_packageversion_wrong_pkg():
    """Calling save() with a package version with a wrong package should raise ValidationError."""
    package = Package.objects.get(name='nodejs')
    image_package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='gcc-9')
    image_package.package = package

    with pytest.raises(ValidationError, match='Package name mismatch'):
        image_package.save()


def test_packageversion_wrong_upgrade():
    """Calling save() with an upgradable package version with a wrong package should raise ValidationError."""
    package = Package.objects.get(name='gcc-9')
    image_package = models.ImagePackage.objects.get(image__name=IMAGENAME, package__name='nodejs')
    image_package.upgradable_imagepackage = package

    with pytest.raises(ValidationError, match='Upgradable package name mismatch'):
        image_package.save()
