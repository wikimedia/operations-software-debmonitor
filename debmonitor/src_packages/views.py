import json

from django.db.models import Count, Prefetch
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

from debmonitor import DistinctGroupConcat
from bin_packages.models import PackageVersion
from src_packages.models import SrcPackage, SrcPackageVersion


@require_safe
def index(request):
    """Source packages list page."""
    packages = SrcPackage.objects.all().annotate(
        versions_count=Count('versions', distinct=True), os_list=DistinctGroupConcat('versions__os__name'))

    table_headers = [
        {'title': 'Package', 'tooltip': 'Name of the source package'},
        {'title': '# Versions', 'tooltip': 'Number of distinct versions of this source package the hosts that have '
         'binary packages derived from it have installed'},
        {'title': 'Operating Systems',
         'tooltip': ('List of distinct Operating Systems the hosts that have binary packages derived from this source '
                     'package installed are running')},
    ]

    args = {
        'datatables_page_length': 50,
        'packages': packages,
        'section': 'src_packages',
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Source Packages',
    }
    return render(request, 'src_packages/index.html', args)


@require_safe
def detail(request, name):
    """Source package detail page."""
    package_versions = SrcPackageVersion.objects.filter(src_package__name=name).prefetch_related(
        Prefetch('binaries', queryset=PackageVersion.objects.filter(src_package_version__src_package__name=name)))

    if len(package_versions) == 0:
        raise Http404

    table_headers = [
        {'title': 'OS', 'tooltip': 'Operating System'},
        {'title': 'Version', 'tooltip': 'Version of this source package'},
        {'title': 'Binary packages',
         'tooltip': 'List of tracked binary package names that derives from this source package'},
    ]

    args = {
        'datatables_page_length': 50,
        # The IDs are DataTable column IDs.
        'default_order': json.dumps([[0, 'asc'], [1, 'asc']]),
        'package_versions': package_versions,
        'section': 'src_packages',
        'subtitle': 'Source Package',
        'table_headers': table_headers,
        'title': package_versions[0].src_package.name,
    }
    return render(request, 'src_packages/detail.html', args)
