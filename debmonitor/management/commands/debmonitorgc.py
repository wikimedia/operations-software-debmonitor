from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from bin_packages.models import Package, PackageVersion
from kernels.models import KernelVersion
from images.models import Image
from src_packages.models import SrcPackage, SrcPackageVersion


class Command(BaseCommand):
    """Add a custom command to Django's manage.py."""

    help = 'Perform garbage collection of orphaned objects not referenced anymore'
    requires_migrations_checks = True

    def handle(self, *args, **options):
        """Run the garbage collection."""
        # GC old images until they will be deleted when deprecated externally from Debmonitor
        res = Image.objects.select_related(None).filter(modified__lt=timezone.now() - timedelta(days=90)).delete()
        # Getting the specific counter of Images deleted because the Django reported total number of deleted objects
        # includes also the ones deleted by cascade constrains like the ImagePackage objects.
        # The returned structure is:
        # (total_deleted_objects, {object_type: deleted_objects, ...})
        # (828, {'images.Image': 5, 'images.ImagePackage': 823})
        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} Image objects not updated in the last 90 days'.format(
                count=res[1].get('images.Image', 0))))

        # Searching the packages to delete in Python as doing it in a single query makes it explode in terms of explain
        sets = []
        for column in ('installed_hosts', 'upgradable_hosts', 'installed_images', 'upgradable_images'):
            sets.append(set(
                PackageVersion.objects.select_related(None).annotate(
                    count=Count(column, distinct=True)).filter(count=0)))

        primary_keys = [pkg.pk for pkg in set.intersection(*sets)]

        # Delete in chunks of 1000 package versions at a time
        primary_keys_groups = [primary_keys[i:i + 1000] for i in range(0, len(primary_keys), 1000)]
        res = 0
        for primary_keys_group in primary_keys_groups:
            partial_res = PackageVersion.objects.select_related(None).filter(pk__in=primary_keys_group).delete()
            res += partial_res[0]

        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} PackageVersion objects not referenced by any HostPackage or ImagePackage'.
            format(count=res)))

        res = Package.objects.select_related(None).annotate(
            versions_count=Count('versions', distinct=True)).filter(versions_count=0).order_by().delete()
        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} Package objects not referenced by any PackageVersion'.format(count=res[0])))

        res = SrcPackageVersion.objects.select_related(None).annotate(
            binaries_count=Count('binaries', distinct=True)).filter(binaries_count=0).order_by().delete()
        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} SrcPackageVersion objects not referenced by any PackageVersion'.format(count=res[0])))

        res = SrcPackage.objects.select_related(None).annotate(
            versions_count=Count('versions', distinct=True)).filter(versions_count=0).order_by().delete()
        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} SrcPackage objects not referenced by any SrcPackageVersion'.format(count=res[0])))

        res = KernelVersion.objects.select_related(None).annotate(
            hosts_count=Count('hosts', distinct=True)).filter(hosts_count=0).order_by().delete()
        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} KernelVersion objects not referenced by any Host'.format(count=res[0])))
