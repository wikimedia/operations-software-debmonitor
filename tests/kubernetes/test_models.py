import pytest

from kubernetes.models import KubernetesImage

pytestmark = pytest.mark.django_db


def test_kubernetesimage_str():
    """The string representation of a KubernetesImage should return cluster, namespace and image name."""
    image = KubernetesImage.objects.all()[0]
    assert str(image) == 'ClusterA - NamespaceA - registry.example.com/component/image-deployed:1.2.3-1'
