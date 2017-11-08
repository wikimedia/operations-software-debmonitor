import json

from collections import defaultdict, OrderedDict

from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

from bin_packages.models import Package, PackageVersion
from debmonitor import DistinctGroupConcat
from hosts.models import HostPackage, SECURITY_UPGRADE


@require_safe
def index(request):
    """Binary packages list page."""
    packages = Package.objects.annotate(
        hosts_count=Count('installed_hosts', distinct=True),
        upgrades_count=Count('upgradable_hosts', distinct=True),
        versions_count=Count('versions', distinct=True),
        os_list=DistinctGroupConcat('versions__os__name'))

    upgrades = HostPackage.objects.select_related(None).filter(upgrade_type=SECURITY_UPGRADE).values(
        'package').annotate(Count('host', distinct=True)).order_by('package')
    security_upgrades = {upgrade['package']: upgrade['host__count'] for upgrade in upgrades}

    table_headers = [
        {'title': 'Package', 'tooltip': 'Name of the binary package', 'badges': [
         {'style': 'primary', 'tooltip': 'Number of hosts that have this package installed'},
         {'style': 'warning', 'tooltip': 'Number of hosts that have this package installed and are pending an upgrade'},
         {'style': 'danger',
          'tooltip': 'Number of hosts that have this package installed and are pending a security upgrade'}]},
        {'title': '# Versions',
         'tooltip': 'Number of distinct installed versions of this package between all the hosts'},
        {'title': 'OSes',
         'tooltip': 'List of distinct Operating Systems the hosts that have this package installed are running'},
        {'title': '# Hosts'},
        {'title': '# Upgrades'},
        {'title': '# Security Upgrades'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'custom_sort': {'name': 'Package', 'installed': 3, 'upgrades': 4, 'security': 5},
        'datatables_column_defs': json.dumps([
            {'targets': [3, 4, 5], 'visible': False, 'searchable': False, 'sortable': False}]),
        'packages': packages,
        'section': 'bin_packages',
        'security_upgrades': security_upgrades,
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Binary Packages',
    }
    return render(request, 'bin_packages/index.html', args)


@require_safe
def detail(request, name):
    """Binary package detail page."""
    package_versions = PackageVersion.objects.filter(package__name=name).annotate(
        hosts_count=Count('installed_hosts', distinct=True), upgrades_count=Count('upgradable_hosts', distinct=True))

    if not package_versions:
        raise Http404

    host_packages = HostPackage.objects.filter(package__name=name)
    upgrades = HostPackage.objects.select_related(None).filter(
        package__name=name, upgrade_type=SECURITY_UPGRADE).values('upgradable_version').annotate(
        Count('host', distinct=True)).order_by('upgradable_version')
    security_upgrades = {upgrade['upgradable_version']: upgrade['host__count'] for upgrade in upgrades}

    os_versions = OrderedDict()
    src_packages_versions = set()
    for package_version in package_versions:
        os = package_version.os.name
        ver = package_version.version

        if os not in os_versions:
            os_versions[os] = {'versions': OrderedDict(), 'totals': {}}

        os_versions[os]['versions'][ver] = defaultdict(int)
        os_versions[os]['versions'][ver]['installed'] += package_version.hosts_count
        os_versions[os]['versions'][ver]['upgradable'] += package_version.upgrades_count
        os_versions[os]['versions'][ver]['security'] += security_upgrades.get(package_version.id, 0)
        src_packages_versions.add(package_version.src_package_version.src_package.name)

    for os_data in os_versions.values():
        totals = defaultdict(int)
        for counter in os_data['versions'].values():
            totals['installed'] += counter['installed']
            totals['upgradable'] += counter['upgradable']
            totals['security'] += counter['security']
        os_data['totals'] = totals

    table_headers = [
        {'title': 'OS'},
        {'title': 'Version'},
        {'title': 'Hostname', 'tooltip': 'Host that have this specific combination of OS and version installed'},
        {'title': 'Upgradable to', 'tooltip': 'Version to which the package can be upgraded to'},
        {'title': 'Upgrade Type'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'column_grouping': {'columns': [0, 1], 'column_titles': ['OS', 'Version']},
        'default_order': json.dumps([[0, 'asc'], [1, 'asc']]),
        'datatables_column_defs': json.dumps([
            {'targets': [0, 1, 4], 'visible': False, 'sortable': False}, {'targets': [3], 'sortable': False}]),
        'host_packages': host_packages,
        'os_versions': os_versions,
        'package_versions': package_versions,
        'section': 'bin_packages',
        'src_packages_versions': src_packages_versions,
        'subtitle': 'Binary Package',
        'table_headers': table_headers,
        'title': name,
        'upgrades_column': 3,
    }
    return render(request, 'bin_packages/detail.html', args)
