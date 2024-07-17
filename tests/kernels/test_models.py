import pytest

from django.utils.text import slugify

from kernels.models import KernelVersion
from src_packages.models import OS

pytestmark = pytest.mark.django_db


def test_kernel_save_slug():
    """Saving a new kernel should automatically populate the slug field."""
    os = OS.objects.get(name='Debian 11')
    name = 'Running Kernel 1.0.0-1'
    kernel = KernelVersion(name=name, os=os)
    kernel.save()
    assert kernel.slug == slugify(name)
