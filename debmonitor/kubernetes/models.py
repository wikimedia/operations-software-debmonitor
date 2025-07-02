from django.db import models

from images.models import Image


class KubernetesImage(models.Model):
    """Model for Images deployes on Kubernetes clusters."""

    cluster = models.CharField(max_length=255, help_text='Kubernetes cluster name.')
    namespace = models.CharField(max_length=255, help_text='Kubernetes cluster namespace name.')
    image = models.ForeignKey(
        Image, on_delete=models.PROTECT, related_name='namespaces', verbose_name='image',
        help_text='Container image deployed in this Kubernetes cluster and namespace.')
    containers = models.PositiveIntegerField(
        help_text='How many running containers in this cluster and namespace this image has.',
    )

    created = models.DateTimeField(auto_now_add=True, help_text='Datetime of the creation of this object.')
    modified = models.DateTimeField(auto_now=True, help_text='Datetime of the last modification of this object.')

    class Meta:
        """Additional metadata."""

        ordering = ['cluster', 'namespace', 'image']
        unique_together = ('cluster', 'namespace', 'image')
        verbose_name = 'kubernetes'
        verbose_name_plural = 'kubernetes'

    def __str__(self):
        """Model representation."""
        return f'{self.cluster} - {self.namespace} - {self.image.name}'
