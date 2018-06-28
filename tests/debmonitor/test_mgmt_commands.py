from io import StringIO

import pytest

from django.core.management import call_command

from hosts.models import HostPackage


@pytest.mark.django_db
def test_command_output_noop():
    """Calling the custom debmonitorgc command should run the garbage collection in the DB as a noop."""
    out = StringIO()
    call_command('debmonitorgc', stdout=out)

    objects = (
        ('PackageVersion', 'HostPackage'),
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
        (6, 'PackageVersion', 'HostPackage'),
        (4, 'Package', 'PackageVersion'),
        (5, 'SrcPackageVersion', 'PackageVersion'),
        (3, 'SrcPackage', 'SrcPackageVersion'),
    )

    for num, obj, ref_obj in objects:
        message = 'Deleted {num} {obj} objects not referenced by any {ref_obj}'.format(
            num=num, obj=obj, ref_obj=ref_obj)
        assert message in out.getvalue()
