from django.core.exceptions import ValidationError
from django.db import models

from bin_packages.models import Package, PackageVersion
from debmonitor import SelectManager
from src_packages.models import OS


SECURITY_UPGRADE = 'security'


class Image(models.Model):
    """Container image model"""

    name = models.CharField(max_length=255, unique=True, help_text='Container image name')
    os = models.ForeignKey(OS, on_delete=models.PROTECT, related_name='+', verbose_name='operating system',
                           help_text='Operating system.')
    packages = models.ManyToManyField(
        Package, related_name='+', through='ImagePackage', through_fields=('image', 'package'),
        db_index=True, blank=True, verbose_name='binary packages',
        help_text='Binary packages installed in this container image')
    package_versions = models.ManyToManyField(
        PackageVersion, related_name='+', through='ImagePackage', through_fields=('image', 'package_version'),
        db_index=True, blank=True, verbose_name='binary package versions',
        help_text='Binary package versions installed in this container image')
    upgradable_imagepackages = models.ManyToManyField(
        Package, related_name='+', through='ImagePackage', through_fields=('image', 'upgradable_imagepackage'),
        db_index=True, blank=True, verbose_name='upgradable binary packages',
        help_text='Binary packages installed on this image that could be upgraded.')
    upgradable_versions = models.ManyToManyField(
        PackageVersion, related_name='+', through='ImagePackage', through_fields=('image', 'upgradable_imageversion'),
        db_index=True, blank=True, verbose_name='upgradable binary package versions',
        help_text='Binary package versions installed on this image that could be upgraded.')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SelectManager(_select_related=['os'])

    class Meta:
        """Additional metadata."""

        ordering = ['name']
        verbose_name = 'image'
        verbose_name_plural = 'images'

    def __str__(self):
        """Model representation."""
        return self.name

    @classmethod
    def _check_m2m_through_same_relationship(cls):
        return []  # Disable models.E003 check for this model


class ImagePackage(models.Model):
    """Container image packages many-to-many relationship."""

    image = models.ForeignKey(Image, db_index=True, on_delete=models.CASCADE, related_name='+',
                              help_text='Container image package name')
    package = models.ForeignKey(
        Package, db_index=True, on_delete=models.PROTECT, related_name='installed_images',
        verbose_name='binary package', help_text='Binary package.')
    package_version = models.ForeignKey(
        PackageVersion, db_index=True, on_delete=models.PROTECT, related_name='installed_images',
        verbose_name='binary package version', help_text='Binary package version.')
    upgradable_imagepackage = models.ForeignKey(
        Package, db_index=True, on_delete=models.PROTECT, related_name='upgradable_images', blank=True, null=True,
        verbose_name='upgradable binary package', help_text='Upgradable binary package.')
    upgradable_imageversion = models.ForeignKey(
        PackageVersion, db_index=True, on_delete=models.PROTECT, related_name='upgradable_images',
        blank=True, null=True,
        verbose_name='upgradable binary package version', help_text='Upgradable binary package version.')
    upgrade_type = models.CharField(max_length=255, blank=True, null=True, help_text='Upgrade type (security)')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SelectManager(_select_related=['image', 'image__os', 'package', 'package_version__package',
                                             'package_version__os', 'upgradable_imagepackage',
                                             'package_version__src_package_version__src_package',
                                             'upgradable_imageversion__package', 'upgradable_imageversion__os'])

    class Meta:
        """Additional metadata."""

        ordering = ['image__name', 'package__name', 'package_version__version']
        unique_together = ('image', 'package')
        verbose_name = 'image package'
        verbose_name_plural = 'image packages'

    def __str__(self):
        """Model representation."""
        if self.upgradable_imageversion is not None:
            to_ver = self.upgradable_imageversion.version
        else:
            to_ver = '-'

        return '{image}: {pkg} ({from_ver} -> {to_ver})'.format(
            image=self.image.name, pkg=self.package.name, from_ver=self.package_version.version, to_ver=to_ver)

    def clean(self):
        """Validate the model fields."""
        package_errors = []
        upgradable_errors = []

        if self.package_version.os != self.image.os:
            package_errors.append('OS mismatch between {bin} and {image} ({image_os})'.format(
                bin=str(self.package_version), image=self.image.name, image_os=self.image.os))

        if self.package_version.package != self.package:
            package_errors.append('Package name mismatch between version of {ver} and {pkg}'.format(
                ver=self.package_version.package.name, pkg=self.package.name))

        if self.upgradable_imageversion is not None and self.upgradable_imageversion.os != self.image.os:
            upgradable_errors.append('OS mismatch between {bin} and {image} ({image_os})'.format(
                bin=str(self.upgradable_imageversion), image=self.image.name, image_os=self.image.os))

        if (self.upgradable_imageversion is not None and
                self.upgradable_imageversion.package != self.upgradable_imagepackage):
            upgradable_errors.append(
                'Upgradable package name mismatch between version of {ver} and {pkg}'.format(
                    ver=self.upgradable_imageversion.package.name, pkg=self.upgradable_imagepackage.name))

        errors = {}
        if package_errors:
            errors['package_version'] = '; '.join(package_errors)
        if upgradable_errors:
            errors['upgradable_version'] = '; '.join(upgradable_errors)

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override parent save() to force validation."""
        self.full_clean()
        super().save(*args, **kwargs)
