from django.core.validators import RegexValidator
from django.db import models

from debmonitor import SelectManager


class OS(models.Model):
    """Operating system model."""

    validation_regex = r'^(Debian( \d\d)?|Ubuntu( \d\d\.\d\d)?)$'
    name = models.CharField(
        max_length=32, unique=True, help_text='Operating system name.',
        validators=[
            RegexValidator(
                regex=validation_regex,
                message=(
                    "The OS name needs to follow the following pattern: "
                    f"{validation_regex}")
            ),
        ])

    class Meta:
        """Additional metadata."""

        verbose_name = 'operating system'
        verbose_name_plural = 'operating systems'

    def __str__(self):
        """Model representation."""
        return self.name


class SrcPackage(models.Model):
    """Source package model."""

    name = models.CharField(max_length=255, unique=True, help_text='Source package name.')

    class Meta:
        """Additional metadata."""

        ordering = ['name']
        verbose_name = 'source package'
        verbose_name_plural = 'source packages'

    def __str__(self):
        """Model representation."""
        return self.name


class SrcPackageVersionManager(SelectManager):
    """Manager class for the PackageVersion model."""

    def get_or_create(self, **kwargs):
        """Override parent method to lazily create the missing objects."""
        arguments = {'version': kwargs['version'], 'os': kwargs['os']}
        if ('src_package' in kwargs and kwargs['src_package'] is not None and
                kwargs['src_package'].name == kwargs['name']):  # Use already queried objects
            arguments['src_package'] = kwargs['src_package']
        else:
            arguments['src_package'], _ = SrcPackage.objects.get_or_create(name=kwargs['name'])

        return super().get_or_create(**arguments)


class SrcPackageVersion(models.Model):
    """Source package version model."""

    src_package = models.ForeignKey(SrcPackage, on_delete=models.PROTECT, db_index=False, related_name='versions',
                                    verbose_name='source package', help_text='Source package.')
    version = models.CharField(max_length=255, help_text='Version.')
    os = models.ForeignKey(OS, on_delete=models.PROTECT, db_index=False, related_name='+',
                           help_text='Operating system.')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SrcPackageVersionManager(_select_related=['src_package', 'os'])

    class Meta:
        """Additional metadata."""

        ordering = ['src_package__name', 'os__name', 'version']
        unique_together = ('src_package', 'version', 'os')
        verbose_name = 'source package version'
        verbose_name_plural = 'source package versions'

    def __str__(self):
        """Model representation."""
        return '{name} {version} ({os})'.format(name=self.src_package.name, version=self.version, os=self.os.name)
