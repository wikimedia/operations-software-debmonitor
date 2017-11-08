from django.db.models import Count, Max, Min
from django.shortcuts import render
from django.views.decorators.http import require_safe

from bin_packages.models import Package, PackageVersion
from hosts.models import Host, HostPackage, SECURITY_UPGRADE
from src_packages.models import SrcPackage, SrcPackageVersion


@require_safe
def index(request):
    """Homepage."""
    hosts = Host.objects.values('modified').aggregate(
        Max('modified'),
        Min('modified'),
        Count('pk'))
    upgradable = HostPackage.objects.exclude(upgradable_package__isnull=True).aggregate(
        Count('host', distinct=True),
        Count('upgradable_package', distinct=True),
        Count('upgradable_version', distinct=True),
        Count('pk'))
    security_upgrades = HostPackage.objects.exclude(upgradable_package__isnull=True).filter(
        upgrade_type__startswith=SECURITY_UPGRADE).aggregate(
        Count('host', distinct=True),
        Count('upgradable_package', distinct=True),
        Count('upgradable_version', distinct=True),
        Count('pk'))

    counters = [
        {'title': 'Hosts', 'count': hosts['pk__count'], 'url': 'hosts', 'rows': [
            {'title': 'With pending upgrades', 'count': upgradable['host__count'], 'style': 'warning'},
            {'title': 'With pending security upgrades', 'count': security_upgrades['host__count'], 'style': 'danger'},
        ]},
        {'title': 'Kernels', 'count': Host.objects.values('running_kernel_slug').distinct().count(), 'url': 'kernels',
         'rows': []},
        {'title': 'Binary Packages', 'count': Package.objects.count(), 'url': 'bin_packages', 'rows': [
            {'title': 'With upgrades', 'count': upgradable['upgradable_package__count'], 'style': 'warning'},
            {'title': 'With security upgrades', 'count': security_upgrades['upgradable_package__count'],
             'style': 'danger'},
        ]},
        {'title': 'Source Packages', 'count': SrcPackage.objects.count(), 'url': 'src_packages', 'rows': [
            {'title': 'Distinct versions', 'count': SrcPackageVersion.objects.count(), 'style': 'secondary'},
        ]},
        {'title': 'Binary Versions', 'count': PackageVersion.objects.count(), 'url': 'bin_packages', 'rows': [
            {'title': 'With upgrades', 'count': upgradable['upgradable_version__count'], 'style': 'warning'},
            {'title': 'With security upgrades', 'count': security_upgrades['upgradable_version__count'],
             'style': 'danger'},
        ]},
    ]

    args = {
        'updates': [
            {'title': 'Latest', 'value': hosts['modified__max']},
            {'title': 'Oldest', 'value': hosts['modified__min']},
        ],
        'counters': counters,
        'subtitle': 'Debian packages tracker',
        'title': 'DebMonitor',
        'totals': [
            {'title': 'Pending upgrades', 'count': upgradable['pk__count'],
             'tooltip': 'Number of pending upgrades across all hosts', 'style': 'warning'},
            {'title': 'Security upgrades', 'count': security_upgrades['pk__count'],
             'tooltip': 'Number of pending security upgrades across all hosts', 'style': 'danger'},
        ],
    }

    return render(request, 'index.html', args)
