import json

from collections import defaultdict, OrderedDict

from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

from bin_packages.models import Package, PackageVersion
from debmonitor import DistinctGroupConcat
from hosts.models import HostPackage, SECURITY_UPGRADE
from images.models import ImagePackage


def _count_items_per_package(model, count_field, filters=None):
    """Return a dictionary with package as key and the count of field items as value for all packages."""
    if filters is None:
        filters = {}

    return {row[count_field]: row['count'] for row in model.objects.select_related(None).filter(**filters).values(
        count_field).annotate(count=Count(count_field)).order_by()}


def _count_items_per_version(model, package_id, count_field, filters=None):
    """Return a dictionary with package version as key and the count of field items as value for a given package."""
    exclude = {'{field}__isnull'.format(field=count_field): True}
    if filters is None:
        filters = {}

    return {row[count_field]: row['count'] for row in model.objects.select_related(None).filter(
        package=package_id, **filters).exclude(**exclude).values(count_field).annotate(count=Count(
            count_field)).order_by()}


@require_safe
def index(request):
    """Binary packages list page."""
    packages = Package.objects.annotate(
        versions_count=Count('versions', distinct=True),
        os_list=DistinctGroupConcat('versions__os__name'))

    # Get all the additional annotations separately for query optimization purposes
    package_annotations = {'hosts': {}, 'images': {}}
    package_annotations['hosts']['inst_count'] = _count_items_per_package(HostPackage, 'package')
    package_annotations['hosts']['upgrades_count'] = _count_items_per_package(HostPackage, 'upgradable_package')
    package_annotations['hosts']['security_count'] = _count_items_per_package(
        HostPackage, 'upgradable_package', filters={'upgrade_type': SECURITY_UPGRADE})
    package_annotations['images']['inst_count'] = _count_items_per_package(ImagePackage, 'package')
    package_annotations['images']['upgrades_count'] = _count_items_per_package(ImagePackage, 'upgradable_imagepackage')
    package_annotations['images']['security_count'] = _count_items_per_package(
        ImagePackage, 'upgradable_imagepackage', filters={'upgrade_type': SECURITY_UPGRADE})

    # Insert all the annotated data back into the package objects for easy access in the templates
    for package in packages:
        for annotation in ('inst_count', 'upgrades_count', 'security_count'):
            setattr(package, annotation, package_annotations['hosts'][annotation].get(package.id, 0)
                    + package_annotations['images'][annotation].get(package.id, 0))

    table_headers = [
        {'title': 'Package', 'tooltip': 'Name of the binary package', 'badges': [
         {'style': 'primary', 'tooltip': 'Number of hosts/images that have this package installed'},
         {'style': 'warning',
          'tooltip': 'Number of hosts/images that have this package installed and are pending an upgrade'},
         {'style': 'danger',
          'tooltip': 'Number of hosts/images that have this package installed and are pending a security upgrade'}]},
        {'title': '# Versions',
         'tooltip': 'Number of distinct installed versions of this package between all the hosts/images'},
        {'title': 'OSes',
         'tooltip': 'List of distinct operating systems the hosts/images that have this package installed are running'},
        {'title': '# Hosts'},
        {'title': '# Upgrades'},
        {'title': '# Security Upgrades'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'custom_sort': {'name': 'Package', 'installed': 3, 'upgrades': 4, 'security': 5},
        'datatables_column_defs': json.dumps([
            {'targets': [3, 4, 5], 'visible': False},
            {'targets': [1, 2, 3, 4, 5], 'searchable': False},
            {'targets': [3, 4, 5], 'sortable': False}]),
        'datatables_page_length': 50,
        'packages': packages,
        'section': 'bin_packages',
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Binary Packages',
    }
    return render(request, 'bin_packages/index.html', args)


@require_safe
def detail(request, name):
    """Binary package detail page."""
    package_versions = PackageVersion.objects.filter(package__name=name)
    if not package_versions:
        raise Http404

    package_id = package_versions[0].package
    counters = {'hosts': {}, 'images': {}}
    counters['hosts']['package_version'] = _count_items_per_version(HostPackage, package_id, 'package_version')
    counters['hosts']['upgradable_version'] = _count_items_per_version(HostPackage, package_id, 'upgradable_version')
    counters['hosts']['security_upgrades'] = _count_items_per_version(
        HostPackage, package_id, 'upgradable_version', filters={'upgrade_type': SECURITY_UPGRADE})
    counters['images']['package_version'] = _count_items_per_version(ImagePackage, package_id, 'package_version')
    counters['images']['upgradable_version'] = _count_items_per_version(
        ImagePackage, package_id, 'upgradable_imageversion')
    counters['images']['security_upgrades'] = _count_items_per_version(
        ImagePackage, package_id, 'upgradable_imageversion', filters={'upgrade_type': SECURITY_UPGRADE})

    host_packages = HostPackage.objects.filter(package__name=name)
    image_packages = ImagePackage.objects.filter(package__name=name)

    os_versions = OrderedDict()
    src_packages_versions = set()
    for package_version in package_versions:
        os = package_version.os.name
        ver = package_version.version
        ver_id = package_version.id

        if os not in os_versions:
            os_versions[os] = {'versions': OrderedDict(), 'totals': {}}

        os_versions[os]['versions'][ver] = defaultdict(int)
        os_versions[os]['versions'][ver]['installed'] += (
            counters['hosts']['package_version'].get(ver_id, 0)
            + counters['images']['package_version'].get(ver_id, 0))
        os_versions[os]['versions'][ver]['upgradable'] += (
            counters['hosts']['upgradable_version'].get(ver_id, 0)
            + counters['images']['upgradable_version'].get(ver_id, 0))
        os_versions[os]['versions'][ver]['security'] += (
            counters['hosts']['security_upgrades'].get(ver_id, 0)
            + counters['images']['security_upgrades'].get(ver_id, 0))

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
        {'title': 'Hostname/Image name', 'tooltip':
         'Host/image that have this specific combination of OS and version installed'},
        {'title': 'Upgradable to', 'tooltip': 'Version to which the package can be upgraded to'},
        {'title': 'Upgrade Type'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'column_groups': [
            {'column': 0, 'title': 'OS', 'css_group': 1,
             'tooltip': 'Number of hosts/images that have this package and OS installed'},
            {'column': 1, 'title': 'Version', 'css_group': 2,
             'tooltip': 'Number of hosts/images that have this specific package version and OS installed'},
        ],
        'default_order': json.dumps([[0, 'asc'], [1, 'asc']]),
        'datatables_column_defs': json.dumps([
            {'targets': [0, 1], 'searchable': False},
            {'targets': [0, 1, 3, 4], 'sortable': False},
            {'targets': [0, 1, 4], 'visible': False},
        ]),

        'datatables_page_length': 50,
        'host_packages': host_packages,
        'image_packages': image_packages,
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
