import logging

from django import http
from django.db.models import Count, Max, Min
from django.shortcuts import render
from django.views.decorators.http import require_safe
from stronghold.decorators import public

import debmonitor

from bin_packages.models import Package, PackageVersion
from hosts import HostAuthError, verify_clients
from hosts.models import Host, HostPackage, SECURITY_UPGRADE
from src_packages.models import SrcPackage, SrcPackageVersion


CLIENT_VERSION_HEADER = 'X-Debmonitor-Client-Version'
CLIENT_CHECKSUM_HEADER = 'X-Debmonitor-Client-Checksum'
logger = logging.getLogger(__name__)


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


@require_safe
@public
def client(request):
    """Download the DebMonitor CLI script on GET, add custom headers with the version and checksum."""
    try:
        verify_clients(request)
    except HostAuthError as e:
        return http.HttpResponseForbidden(e, content_type='text/plain')

    try:
        version, checksum, body = debmonitor.get_client()
    except Exception as e:  # Force a response to avoid using the HTML template for all other 500s
        message = 'Unable to retrieve client code'
        logger.exception(message)
        return http.HttpResponseServerError('{message}: {e}'.format(message=message, e=e), content_type='text/plain')

    if request.method == 'HEAD':
        response = http.HttpResponse()
    elif request.method == 'GET':
        response = http.HttpResponse(body, content_type='text/x-python')
    else:  # pragma: no cover - this should never happen due to @require_safe
        return http.HttpResponseBadRequest(
            'Invalid method {method}'.format(method=request.method), content_type='text/plain')

    response[CLIENT_VERSION_HEADER] = version
    response[CLIENT_CHECKSUM_HEADER] = checksum

    return response
