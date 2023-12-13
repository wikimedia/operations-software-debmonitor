from django.db import models
from django.utils.text import slugify

from debmonitor import SelectManager
from src_packages.models import OS


class KernelVersion(models.Model):
    """Kernel version."""

    name = models.CharField(max_length=255, help_text='Kernel version.', db_index=True)
    slug = models.SlugField(max_length=255, help_text='Kernel version and OS URL slug.')
    os = models.ForeignKey(OS, on_delete=models.PROTECT, related_name='+', verbose_name='operating system',
                           help_text='Operating system.')

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    objects = SelectManager(_select_related=['os'])

    class Meta:
        """Additional metadata."""

        ordering = ['os__name', 'name']
        unique_together = ('name', 'os')
        verbose_name = 'kernel'
        verbose_name_plural = 'kernels'

    def __str__(self):
        """Model representation."""
        return self.name

    def save(self, *args, **kwargs):
        """Override parent method to auto-calculate the running kernel name and OS ID slug."""
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
