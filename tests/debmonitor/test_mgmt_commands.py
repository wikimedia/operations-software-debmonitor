from io import StringIO

import pytest

from django.core.management import call_command
from django.utils import timezone

from hosts.models import Host, HostPackage
from images.models import Image


@pytest.mark.django_db
def test_command_output_noop():
    """Calling the custom debmonitorgc command should run the garbage collection in the DB as a noop."""
    out = StringIO()
    # Update all images and hosts to prevent any deletion.
    Image.objects.select_related(None).update(modified=timezone.now())
    Host.objects.select_related(None).update(modified=timezone.now())
    call_command('debmonitorgc', stdout=out)

    objects = (
        ('PackageVersion', 'HostPackage or ImagePackage'),
        ('Package', 'PackageVersion'),
        ('SrcPackageVersion', 'PackageVersion'),
        ('SrcPackage', 'SrcPackageVersion'),
    )

    for obj, ref_obj in objects:
        message = 'Deleted 0 {obj} objects not referenced by any {ref_obj}'.format(obj=obj, ref_obj=ref_obj)
        assert message in out.getvalue()


@pytest.mark.django_db
def test_command_output_delete():
    """Calling the custom debmonitorgc command with orphaned object should delete them."""
    out = StringIO()
    HostPackage.objects.all().delete()
    call_command('debmonitorgc', stdout=out)

    objects = (
        (8, 'PackageVersion', 'HostPackage or ImagePackage'),
        (5, 'Package', 'PackageVersion'),
        (6, 'SrcPackageVersion', 'PackageVersion'),
        (3, 'SrcPackage', 'SrcPackageVersion'),
        (1, 'KernelVersion', 'Host'),
    )

    assert 'Deleted 1 Image objects not updated in the last 90 days' in out.getvalue()
    assert 'Deleted 3 Host objects not updated in the last 15 days' in out.getvalue()
    for num, obj, ref_obj in objects:
        message = 'Deleted {num} {obj} objects not referenced by any {ref_obj}'.format(
            num=num, obj=obj, ref_obj=ref_obj)
        assert message in out.getvalue()
