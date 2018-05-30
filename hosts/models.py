from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from bin_packages.models import Package, PackageVersion
from debmonitor import SelectManager
from src_packages.models import OS


SECURITY_UPGRADE = 'security'


class Host(models.Model):
    """Host model."""

    # TODO: validate hostname according to RFCs 1035, 1123 and 2181. See also RFC 3696
    name = models.CharField(max_length=190, unique=True, help_text='Hostname.')
    os = models.ForeignKey(OS, on_delete=models.PROTECT, related_name='+', verbose_name='operating system',
                           help_text='Operating system.')
    running_kernel = models.CharField(max_length=190, help_text='Running kernel version.')
    running_kernel_slug = models.SlugField(max_length=190, help_text='Running kernel version URL slug.')
    packages = models.ManyToManyField(
        Package, related_name='+', through='HostPackage', through_fields=('host', 'package'),
        db_index=True, blank=True, verbose_name='binary packages', help_text='Binary packages installed on this host.')
    package_versions = models.ManyToManyField(
        PackageVersion, related_name='+', through='HostPackage', through_fields=('host', 'package_version'),
        db_index=True, blank=True, verbose_name='binary package versions',
        help_text='Binary package versions installed on this host.')
    upgradable_packages = models.ManyToManyField(
        Package, related_name='+', through='HostPackage', through_fields=('host', 'upgradable_package'),
        db_index=True, blank=True, verbose_name='upgradable binary packages',
        help_text='Binary packages installed on this host that could be upgraded.')
    upgradable_versions = models.ManyToManyField(
        PackageVersion, related_name='+', through='HostPackage', through_fields=('host', 'upgradable_version'),
        db_index=True, blank=True, verbose_name='upgradable binary package versions',
        help_text='Binary package versions installed on this host that could be upgraded.')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SelectManager(_select_related=['os'])

    class Meta:
        """Additional metadata."""

        ordering = ['name']
        verbose_name = 'host'
        verbose_name_plural = 'hosts'

    def __str__(self):
        """Model representation."""
        return self.name

    def save(self, *args, **kwargs):
        """Override parent method to auto-calculate the running kernel slug."""
        self.running_kernel_slug = slugify(self.running_kernel)
        super().save(*args, **kwargs)

    @classmethod
    def _check_m2m_through_same_relationship(cls):
        return []  # Disable models.E003 check for this model


class HostPackage(models.Model):
    """Hosts packages many-to-many relationship."""

    host = models.ForeignKey(Host, db_index=True, on_delete=models.CASCADE, related_name='+', help_text='Host.')
    package = models.ForeignKey(
        Package, db_index=True, on_delete=models.PROTECT, related_name='installed_hosts',
        verbose_name='binary package', help_text='Binary package.')
    package_version = models.ForeignKey(
        PackageVersion, db_index=True, on_delete=models.PROTECT, related_name='installed_hosts',
        verbose_name='binary package version', help_text='Binary package version.')
    upgradable_package = models.ForeignKey(
        Package, db_index=True, on_delete=models.PROTECT, related_name='upgradable_hosts', blank=True, null=True,
        verbose_name='upgradable binary package', help_text='Upgradable binary package.')
    upgradable_version = models.ForeignKey(
        PackageVersion, db_index=True, on_delete=models.PROTECT, related_name='upgradable_hosts', blank=True, null=True,
        verbose_name='upgradable binary package version', help_text='Upgradable binary package version.')
    upgrade_type = models.CharField(max_length=190, blank=True, null=True, help_text='Upgrade type (security)')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SelectManager(_select_related=[
        'host', 'host__os', 'package', 'package_version__package', 'package_version__os', 'upgradable_package',
        'package_version__src_package_version__src_package', 'upgradable_version__package', 'upgradable_version__os'])

    class Meta:
        """Additional metadata."""

        ordering = ['host__name', 'package__name', 'package_version__version']
        unique_together = ('host', 'package')
        verbose_name = 'host package'
        verbose_name_plural = 'host packages'

    def __str__(self):
        """Model representation."""
        if self.upgradable_version is not None:
            to_ver = self.upgradable_version.version
        else:
            to_ver = '-'

        return '{host}: {pkg} ({from_ver} -> {to_ver})'.format(
            host=self.host.name, pkg=self.package.name, from_ver=self.package_version.version, to_ver=to_ver)

    def clean(self):
        """Validate the model fields."""
        package_errors = []
        upgradable_errors = []

        if self.package_version.os != self.host.os:
            package_errors.append('OS mismatch between {bin} and {host} ({host_os})'.format(
                bin=str(self.package_version), host=self.host.name, host_os=self.host.os))

        if self.package_version.package != self.package:
            package_errors.append('Package name mismatch between version of {ver} and {pkg}'.format(
                ver=self.package_version.package.name, pkg=self.package.name))

        if self.upgradable_version is not None and self.upgradable_version.os != self.host.os:
            upgradable_errors.append('OS mismatch between {bin} and {host} ({host_os})'.format(
                bin=str(self.upgradable_version), host=self.host.name, host_os=self.host.os))

        if self.upgradable_version is not None and self.upgradable_version.package != self.upgradable_package:
            upgradable_errors.append(
                'Upgradable package name mismatch between version of {ver} and {pkg}'.format(
                    ver=self.upgradable_version.package.name, pkg=self.upgradable_package.name))

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
