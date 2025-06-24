import json
import logging

from collections import namedtuple

from django.conf import settings
from django.db.models import Count, F, Max, Min
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_safe

from bin_packages.models import Package, PackageVersion
from hosts.models import Host, HostPackage, SECURITY_UPGRADE
from images.models import Image, ImagePackage
from kernels.models import KernelVersion
from kubernetes.models import KubernetesImage
from src_packages.models import SrcPackage, SrcPackageVersion


CLIENT_VERSION_HEADER = 'X-Debmonitor-Client-Version'
CLIENT_CHECKSUM_HEADER = 'X-Debmonitor-Client-Checksum'
SearchResult = namedtuple('SearchResult', ['title', 'url_name', 'results'])
logger = logging.getLogger(__name__)


@require_safe
def index(request):
    """Homepage."""
    hosts = Host.objects.values('modified').aggregate(
        Max('modified'),
        Min('modified'),
        Count('pk'))
    images = Image.objects.values('modified').aggregate(
        Max('modified'),
        Min('modified'),
        Count('pk'))
    upgradable = HostPackage.objects.exclude(upgradable_package__isnull=True).aggregate(
        Count('host', distinct=True),
        Count('upgradable_package', distinct=True),
        Count('upgradable_version', distinct=True),
        Count('pk'))
    upgradable_images = ImagePackage.objects.exclude(upgradable_imagepackage__isnull=True).aggregate(
        Count('image', distinct=True),
        Count('upgradable_imagepackage', distinct=True),
        Count('upgradable_imageversion', distinct=True),
        Count('pk'))
    security_upgrades = HostPackage.objects.exclude(upgradable_package__isnull=True).filter(
        upgrade_type__startswith=SECURITY_UPGRADE).aggregate(
        Count('host', distinct=True),
        Count('upgradable_package', distinct=True),
        Count('upgradable_version', distinct=True),
        Count('pk'))
    security_upgrades_images = ImagePackage.objects.exclude(upgradable_imagepackage__isnull=True).filter(
        upgrade_type__startswith=SECURITY_UPGRADE).aggregate(
        Count('image', distinct=True),
        Count('upgradable_imagepackage', distinct=True),
        Count('upgradable_imageversion', distinct=True),
        Count('pk'))

    counters = [
        {'title': 'Hosts', 'count': hosts['pk__count'], 'url': 'hosts', 'rows': [
            {'title': 'With pending upgrades', 'count': upgradable['host__count'], 'style': 'warning'},
            {'title': 'With pending security upgrades', 'count': security_upgrades['host__count'], 'style': 'danger'},
        ]},
        {'title': 'Kernels', 'count': KernelVersion.objects.count(), 'url': 'kernels',
         'rows': []},
        {'title': 'Live Kubernetes Images', 'count': KubernetesImage.objects.count(), 'url': 'kubernetes', 'rows': []},
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
        {'title': 'Images', 'count': images['pk__count'], 'url': 'images', 'rows': [
            {'title': 'With pending upgrades', 'count': upgradable_images['image__count'], 'style': 'warning'},
            {'title': 'With pending security upgrades',
             'count': security_upgrades_images['image__count'], 'style': 'danger'},
        ]},
    ]

    args = {
        'updates': [
            {'title': 'Latest', 'value': hosts['modified__max']},
            {'title': 'Oldest', 'value': hosts['modified__min']},
        ],
        'image_updates': [
            {'title': 'Latest', 'value': images['modified__max']},
            {'title': 'Oldest', 'value': images['modified__min']},
        ],
        'counters': counters,
        'subtitle': 'Debian packages tracker',
        'title': 'DebMonitor',
        'totals': [
            {'title': 'Pending host upgrades', 'count': upgradable['pk__count'],
             'tooltip': 'Number of pending upgrades across all hosts', 'style': 'warning'},
            {'title': 'Pending image upgrades', 'count': upgradable_images['pk__count'],
             'tooltip': 'Number of pending upgrades across all images', 'style': 'warning'},
            {'title': 'Security upgrades (hosts)', 'count': security_upgrades['pk__count'],
             'tooltip': 'Number of pending security upgrades across all hosts', 'style': 'danger'},
            {'title': 'Security upgrades (images)', 'count': security_upgrades_images['pk__count'],
             'tooltip': 'Number of pending security upgrades across all images', 'style': 'danger'},
        ],
    }

    return render(request, 'index.html', args)


@require_GET
def search(request):
    search_results = []
    query = request.GET.get('q')

    if query and len(query) >= settings.DEBMONITOR_SEARCH_MIN_LENGTH:
        search_results = [
            SearchResult(title='Hosts', url_name='hosts:detail',
                         results=Host.objects.filter(name__contains=query).select_related(None).values('name')),
            SearchResult(title='Images', url_name='images:detail',
                         results=Image.objects.filter(name__contains=query).select_related(None).values('name')),
            SearchResult(title='Packages', url_name='bin_packages:detail',
                         results=Package.objects.filter(name__contains=query).select_related(None).values('name')),
            SearchResult(title='Source Packages', url_name='src_packages:detail',
                         results=SrcPackage.objects.filter(name__contains=query).select_related(None).values('name')),
            SearchResult(title='Kernels', url_name='kernels:detail',
                         results=KernelVersion.objects.filter(name__contains=query).select_related(None)),
            SearchResult(title='Package Versions', url_name='bin_packages:detail',
                         results=PackageVersion.objects.filter(version__contains=query).select_related(
                            'package').annotate(name=F('package__name')).values('name', 'version', 'os__name')),
            SearchResult(title='Source Package Versions', url_name='src_packages:detail',
                         results=SrcPackageVersion.objects.filter(version__contains=query).select_related(
                            'src_package').annotate(name=F('src_package__name')).values('name', 'version', 'os__name')),
        ]

    args = {
        # The IDs are DataTable column IDs.
        'column_groups': [
            {'column': 0, 'title': 'Type', 'css_group': 1, 'tooltip': 'Number of objects of this type found'}],
        'default_order': json.dumps([[0, 'asc']]),
        'datatables_column_defs': json.dumps([{'targets': [0], 'visible': False, 'sortable': False}]),
        'datatables_page_length': 50,
        'subtitle': query,
        'table_headers': [{'title': 'Type'}, {'title': 'Name'}],
        'title': 'Search Results',
        'search_results': search_results,
    }

    return render(request, 'search.html', args)
