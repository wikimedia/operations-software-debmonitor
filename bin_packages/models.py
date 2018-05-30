from django.core.exceptions import ValidationError
from django.db import models

from debmonitor import SelectManager
from src_packages.models import OS, SrcPackageVersion


class Package(models.Model):
    """Binary package model."""

    name = models.CharField(max_length=190, unique=True, help_text='Binary package name.')

    class Meta:
        """Additional metadata."""

        ordering = ['name']
        verbose_name = 'package'
        verbose_name_plural = 'packages'

    def __str__(self):
        """Model representation."""
        return self.name


class PackageVersionManager(SelectManager):
    """Manager class for the PackageVersion model."""

    def get_or_create(self, **kwargs):
        """Override parent method to lazily create the missing objects."""
        arguments = {'version': kwargs['version'], 'os': kwargs['os']}
        if 'host_package' in kwargs and kwargs['host_package'] is not None:  # Use already queried objects
            arguments['package'] = kwargs['host_package'].package_version.package
            src_package = kwargs['host_package'].package_version.src_package_version.src_package
        else:
            arguments['package'], _ = Package.objects.get_or_create(name=kwargs['name'])
            src_package = None

        arguments['src_package_version'], _ = SrcPackageVersion.objects.get_or_create(
            name=kwargs['source'], version=kwargs['version'], os=kwargs['os'], src_package=src_package)

        return super().get_or_create(**arguments)


class PackageVersion(models.Model):
    """Binary package version model."""

    package = models.ForeignKey(Package, on_delete=models.PROTECT, db_index=False, related_name='versions',
                                help_text='Binary package.')
    version = models.CharField(max_length=190, help_text='Binary package version.')
    os = models.ForeignKey(OS, on_delete=models.PROTECT, db_index=False, related_name='+',
                           verbose_name='operating system', help_text='Operating system.')
    src_package_version = models.ForeignKey(
        SrcPackageVersion, on_delete=models.PROTECT, related_name='binaries', verbose_name='source package version',
        help_text='Source package version that generated this binary package version.')
    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = PackageVersionManager(
        _select_related=['package', 'os', 'src_package_version', 'src_package_version__src_package'])

    class Meta:
        """Additional metadata."""

        ordering = ['package__name', 'version']
        unique_together = ('package', 'version', 'os')
        verbose_name = 'package version'
        verbose_name_plural = 'package versions'

    def __str__(self):
        """Model representation."""
        return '{name} {version} ({os})'.format(name=self.package.name, version=self.version, os=self.os.name)

    def clean(self):
        """Validate the model fields."""
        if self.os != self.src_package_version.os:
            raise ValidationError('OS mismatch between {src} and {bin}.'.format(
                src=str(self.src_package_version), bin=str(self)))

    def save(self, *args, **kwargs):
        """Override parent save() to force validation."""
        self.full_clean()
        super().save(*args, **kwargs)
