import json
import logging

from django import http
from django.db.models import BooleanField, Case, Count, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe, require_POST
from stronghold.decorators import public

from bin_packages.models import PackageVersion
from hosts import HostAuthError, verify_clients
from hosts.models import Host, HostPackage, SECURITY_UPGRADE
from src_packages.models import OS


try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:  # pragma: notpy34 no cover - Backward compatibility with Python 3.4
    JSONDecodeError = ValueError

TEXT_PLAIN = 'text/plain'
logger = logging.getLogger(__name__)


@require_safe
def index(request):
    """Hosts list page."""
    hosts = Host.objects.annotate(packages_count=Count('packages', distinct=True),
                                  upgrades_count=Count('upgradable_packages', distinct=True))

    upgrades = HostPackage.objects.select_related(None).filter(upgrade_type=SECURITY_UPGRADE).values(
        'host').annotate(Count('package', distinct=True)).order_by('host')
    security_upgrades = {upgrade['host']: upgrade['package__count'] for upgrade in upgrades}

    table_headers = [
        {'title': 'Hostname', 'badges': [
         {'style': 'primary', 'tooltip': 'Number of packages installed in this host'},
         {'style': 'warning', 'tooltip': 'Number of packages pending an upgrade in this host'},
         {'style': 'danger', 'tooltip': 'Number of packages pending a security upgrade in this host'}]},
        {'title': 'OS', 'tooltip': 'Operating System that the host is running'},
        {'title': 'Last update', 'tooltip': 'Last time the host data was updated'},
        {'title': '# Packages'},
        {'title': '# Upgrades'},
        {'title': '# Security Upgrades'},
        {'title': 'Last update timestamp'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'custom_sort': {'name': 'Hostname', 'installed': 3, 'upgrades': 4, 'security': 5},
        'datatables_column_defs': json.dumps([
            {'targets': [3, 4, 5, 6], 'visible': False},
            {'targets': [2], 'orderData': [6]},
            {'targets': [2, 3, 4, 5, 6], 'searchable': False},
        ]),
        'datatables_page_length': 50,
        'hosts': hosts,
        'section': 'hosts',
        'security_upgrades': security_upgrades,
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Hosts',
    }
    return render(request, 'hosts/index.html', args)


@require_safe
def kernel_index(request):
    """Kernels list page."""
    kernels = Host.objects.values('running_kernel_slug', 'os__name', 'running_kernel').annotate(
        hosts_count=Count('running_kernel_slug')).order_by('os__name', 'running_kernel_slug')

    table_headers = [
        {'title': 'OS', 'tooltip': 'Operating System'},
        {'title': 'Kernel', 'tooltip': 'Full version of the running kernel'},
        {'title': '# Hosts', 'tooltip': 'Number of host that are running this kernel'},
    ]

    args = {
        'datatables_column_defs': json.dumps([{'targets': [2], 'searchable': False}]),
        'datatables_page_length': -1,
        'kernels': kernels,
        'section': 'kernels',
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Kernels',
    }
    return render(request, 'kernels/index.html', args)


@require_safe
def detail(request, name):
    """Host detail page."""
    host = get_object_or_404(Host.objects.filter(name=name))
    host_packages = HostPackage.objects.filter(host=host).annotate(
        has_upgrade=Case(
            When(upgradable_version__isnull=False, then=True),
            default=False,
            output_field=BooleanField())
        ).order_by('-has_upgrade', '-upgrade_type', 'package__name')

    table_headers = [
        {'title': 'Package', 'tooltip': 'Name of the binary package'},
        {'title': 'Version', 'tooltip': 'Installed version of this binary package'},
        {'title': 'Upgradable to', 'tooltip': 'Version of this binary package the host can upgrade it to'},
        {'title': 'Upgrade Type'},
    ]

    args = {
        'datatables_column_defs': json.dumps(
            [{'targets': [3], 'visible': False}, {'targets': [1, 2], 'orderable': False}]),
        'datatables_page_length': -1,
        'host': host,
        'host_packages': host_packages,
        'section': 'hosts',
        'subtitle': 'Host',
        'table_headers': table_headers,
        'title': host.name,
        'upgrades_column': 2,
    }
    return render(request, 'hosts/detail.html', args)


@require_safe
def kernel_detail(request, slug):
    """Kernel detail page."""
    hosts = Host.objects.filter(running_kernel_slug=slug).values('name', 'running_kernel')
    if not hosts:
        raise http.Http404

    args = {
        'datatables_page_length': 50,
        'hosts': hosts,
        'section': 'kernels',
        'subtitle': 'Kernel',
        'table_headers': [{'title': 'Hostname'}],
        'title': hosts[0]['running_kernel'],
    }
    return render(request, 'kernels/detail.html', args)


@csrf_exempt
@require_POST
@public
def update(request, name):
    """Update a host and all it's related information from a JSON."""
    try:
        verify_clients(request, hostname=name)
    except HostAuthError as e:
        return http.HttpResponseForbidden(e, content_type=TEXT_PLAIN)

    if not request.body:
        return http.HttpResponseBadRequest("Empty POST, expected JSON string: {req}".format(
            req=request), content_type=TEXT_PLAIN)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except JSONDecodeError as e:
        return http.HttpResponseBadRequest(
            'Unable to parse JSON string payload: {e}'.format(e=e), content_type=TEXT_PLAIN)

    if name != payload.get('hostname', ''):
        return http.HttpResponseBadRequest("URL host '{name}' and POST payload hostname '{host}' do not match".format(
            name=name, host=payload.get('hostname', '')), content_type=TEXT_PLAIN)

    try:
        os = OS.objects.get(name=payload['os'])
    except OS.DoesNotExist as e:
        return http.HttpResponseBadRequest(
            "Unable to find OS '{os}': {e}".format(os=payload['os'], e=e), content_type=TEXT_PLAIN)

    message = "Unable to update host '{host}'".format(host=name)
    try:
        _update_v1(request, name, os, payload)
    except (KeyError, TypeError) as e:
        logger.exception(message)
        return http.HttpResponseBadRequest('{message}: {e}'.format(message=message, e=e), content_type=TEXT_PLAIN)
    except Exception as e:  # Force a response to avoid using the HTML template for all other 500s
        logger.exception(message)
        return http.HttpResponseServerError('{message}: {e}'.format(message=message, e=e), content_type=TEXT_PLAIN)
    else:
        return http.HttpResponse(status=201, content_type=TEXT_PLAIN)


def _update_v1(request, name, os, payload):
    """Update API v1."""
    running_kernel = payload['running_kernel']['version']
    start_time = timezone.now()

    try:
        host = Host.objects.get(name=name)
        host.os = os
        host.running_kernel = running_kernel
        host.save()  # Always update at least the modification time
        host_packages = {host_pkg.package.name: host_pkg for host_pkg in HostPackage.objects.filter(host=host)}

    except Host.DoesNotExist:
        host = Host(name=name, os=os, running_kernel=running_kernel)
        host.save()
        host_packages = {}
        logger.info("Created Host '%s'", name)

    existing_not_updated = []

    installed = payload.get('installed', [])
    for item in installed:
        _process_installed(host, os, host_packages, existing_not_updated, item)

    logger.info("Tracked %d installed packages for host '%s'", len(installed), name)

    uninstalled = payload.get('uninstalled', [])
    for item in uninstalled:
        existing = host_packages.get(item['name'], None)
        if existing is not None:
            existing.delete()

    logger.info("Untracked %d uninstalled packages for host '%s'", len(uninstalled), name)

    upgradable = payload.get('upgradable', [])
    for item in upgradable:
        _process_upgradable(host, os, host_packages, existing_not_updated, item)

    logger.info("Tracked %d upgradable packages for host '%s'", len(upgradable), name)

    if payload['update_type'] == 'full':
        # Delete orphaned entries based on the modification datetime and the list of already up-to-date IDs
        res = HostPackage.objects.filter(host=host, modified__lt=start_time).exclude(
            pk__in=existing_not_updated).delete()
        logger.info("Deleted %d HostPackage orphaned entries for host '%s'", res[0], name)


def _process_installed(host, os, host_packages, existing_not_updated, item):
    """Process an installed package item, return True if it was created or updated."""
    existing = host_packages.get(item['name'], None)

    if existing is not None and existing.package_version.version == item['version']:
        existing_not_updated.append(existing.pk)
        return  # Already up-to-date

    package_version, _ = PackageVersion.objects.get_or_create(os=os, host_package=existing, **item)
    if existing is not None:
        existing.package_version = package_version
        existing.upgradable_package = None
        existing.upgradable_version = None
        existing.upgrade_type = None
        existing.save()
    else:
        host_packages[package_version.package.name] = HostPackage.objects.create(
            host=host, package=package_version.package, package_version=package_version)


def _process_upgradable(host, os, host_packages, existing_not_updated, item):
    """Process an upgradable package item."""
    existing = host_packages.get(item['name'], None)

    if existing is not None:
        if existing.upgradable_package is not None and existing.upgradable_version.version == item['version_to']:
            existing_not_updated.append(existing.pk)
            return  # Already up-to-date

        upgradable_version, _ = PackageVersion.objects.get_or_create(
            os=os, version=item['version_to'], host_package=existing, **item)
        existing.upgradable_package = upgradable_version.package
        existing.upgradable_version = upgradable_version
        existing.save()
    else:
        installed_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_from'], **item)
        upgradable_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_to'], **item)
        HostPackage.objects.create(
            host=host, package=installed_version.package, package_version=installed_version,
            upgradable_package=upgradable_version.package, upgradable_version=upgradable_version)
