from django.core.management.base import BaseCommand
from django.db.models import Count

from bin_packages.models import Package, PackageVersion
from kernels.models import KernelVersion
from src_packages.models import SrcPackage, SrcPackageVersion


class Command(BaseCommand):
    """Add a custom command to Django's manage.py."""

    help = 'Perform garbage collection of orphaned objects not referenced anymore'
    requires_migrations_checks = True

    def handle(self, *args, **options):
        """Run the garbage collection."""
        res = PackageVersion.objects.select_related(None).annotate(
            hosts_count=Count('installed_hosts', distinct=True)).annotate(
            upgrades_count=Count('upgradable_hosts', distinct=True)
            ).filter(hosts_count=0, upgrades_count=0).order_by().delete()

        self.stdout.write(self.style.SUCCESS(
            'Deleted {count} PackageVersion objects not referenced by any HostPackage'.format(count=res[0])))

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
