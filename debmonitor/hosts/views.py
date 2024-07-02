import json
import logging

from collections import defaultdict

from django import http
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import BooleanField, Case, Count, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe, require_POST

from bin_packages.models import PackageVersion
from debmonitor.decorators import verify_clients
from debmonitor.middleware import TEXT_PLAIN
from hosts.models import Host, HostPackage, SECURITY_UPGRADE
from kernels.models import KernelVersion
from src_packages.models import OS


logger = logging.getLogger(__name__)


@require_safe
def index(request):
    """Hosts list page."""
    hosts = Host.objects.all()

    # Get all the additional annotations separately for query optimization purposes
    host_annotations = defaultdict(lambda: defaultdict(int))
    packages_count = Host.objects.select_related(None).values('id').annotate(
        packages_count=Count('packages', distinct=True))
    for host in packages_count:
        host_annotations[host['id']]['packages_count'] = host['packages_count']

    upgrades_count = Host.objects.select_related(None).values('id').annotate(
        upgrades_count=Count('upgradable_packages', distinct=True))
    for host in upgrades_count:
        host_annotations[host['id']]['upgrades_count'] = host['upgrades_count']

    security_count = HostPackage.objects.select_related(None).filter(upgrade_type=SECURITY_UPGRADE).values(
        'host').annotate(security_count=Count('package', distinct=True)).order_by('host')
    for host in security_count:
        host_annotations[host['host']]['security_count'] = host['security_count']

    # Insert all the annotated data back into the package objects for easy access in the templates
    for host in hosts:
        for annotation in ('packages_count', 'upgrades_count', 'security_count'):
            setattr(host, annotation, host_annotations[host.id][annotation])

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
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Hosts',
    }
    return render(request, 'hosts/index.html', args)


class DetailView(View):

    @method_decorator(verify_clients(['DELETE']))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, name):
        """Host detail page."""
        host = get_object_or_404(Host, name=name)

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
            'external_links': {key: value.format(fqdn=host.name, hostname=host.name.split('.')[0])
                               for key, value in settings.DEBMONITOR_HOST_EXTERNAL_LINKS.items()},
            'host': host,
            'host_packages': host_packages,
            'section': 'hosts',
            'subtitle': 'Host',
            'table_headers': table_headers,
            'title': host.name,
            'upgrades_column': 2,
        }
        return render(request, 'hosts/detail.html', args)

    def delete(self, request, name):
        host = get_object_or_404(Host, name=name)
        host.delete()

        return http.HttpResponse(status=204, content_type=TEXT_PLAIN)


@verify_clients
@csrf_exempt
@require_POST
def update(request, name):
    """Update a host and all it's related information from a JSON."""
    if not request.body:
        return http.HttpResponseBadRequest("Empty POST, expected JSON string: {req}".format(
            req=request), content_type=TEXT_PLAIN)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        return http.HttpResponseBadRequest(
            'Unable to parse JSON string payload: {e}'.format(e=e), content_type=TEXT_PLAIN)

    if name != payload.get('hostname', ''):
        return http.HttpResponseBadRequest("URL host '{name}' and POST payload hostname '{host}' do not match".format(
            name=name, host=payload.get('hostname', '')), content_type=TEXT_PLAIN)

    try:
        os = OS.objects.get(name=payload['os'])
    except OS.DoesNotExist as e:
        logger.info(
            "The OS name %s is not present in the DB. Error: %s", payload['os'], e)
        try:
            os = OS(name=payload['os'])
            os.clean_fields()
            os.save()
        except ValidationError as e:
            return http.HttpResponseBadRequest(
                "OS name '{os}' is not valid: {e}".format(os=payload['os'], e=e), content_type=TEXT_PLAIN)

    message = "Unable to update host '{host}'".format(host=name)
    try:
        _update_v1(request, name, os, payload)
    except (KeyError, TypeError) as e:
        logger.exception(message)
        return http.HttpResponseBadRequest('{message}: {e}'.format(message=message, e=e), content_type=TEXT_PLAIN)
    except Exception as e:  # Force a response to avoid using the HTML template for all other 500s
        logger.error(message, exc_info=True)
        return http.HttpResponseServerError('{message}: {e}'.format(message=message, e=e), content_type=TEXT_PLAIN)
    else:
        return http.HttpResponse(status=201, content_type=TEXT_PLAIN)


def _update_v1(request, name, os, payload):
    """Update API v1."""
    start_time = timezone.now()
    kernel, _ = KernelVersion.objects.get_or_create(name=payload['running_kernel']['version'], os=os)

    try:
        host = Host.objects.get(name=name)
        host.os = os
        host.kernel = kernel
        host.save()  # Always update at least the modification time
        host_packages = {host_pkg.package.name: host_pkg for host_pkg in HostPackage.objects.filter(host=host)}

    except Host.DoesNotExist:
        host = Host(name=name, os=os, kernel=kernel)
        host.save()
        host_packages = {}
        logger.info("Created Host '%s'", name)

    existing_not_updated = []
    existing_upgradable_not_updated = []

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
        _process_upgradable(host, os, host_packages, existing_upgradable_not_updated, item)

    logger.info("Tracked %d upgradable packages for host '%s'", len(upgradable), name)

    if payload['update_type'] == 'full':
        _garbage_collection(host, name, start_time, existing_not_updated, existing_upgradable_not_updated)


def _garbage_collection(host, name, start_time, existing_not_updated, existing_upgradable_not_updated):
    # Delete orphaned entries based on the modification datetime and the list of already up-to-date IDs
    res = HostPackage.objects.filter(host=host, modified__lt=start_time).exclude(pk__in=existing_not_updated).delete()
    logger.info("Deleted %d HostPackage orphaned entries for host '%s'", res[0], name)

    # Cleanup orphaned upgrades based on the modification datetime and the list of already up-to-date IDs
    host_packages = HostPackage.objects.filter(
        host=host, modified__lt=start_time, upgradable_package__isnull=False).exclude(
        pk__in=existing_upgradable_not_updated)

    for host_package in host_packages:
        host_package.upgradable_package = None
        host_package.upgradable_version = None
        host_package.upgrade_type = None
        host_package.save()

    logger.info("Cleaned %d HostPackage upgradable info for host '%s'", len(host_packages), name)


def _process_installed(host, os, host_packages, existing_not_updated, item):
    """Process an installed package item, return True if it was created or updated."""
    existing = host_packages.get(item['name'], None)

    if existing is not None and existing.package_version.version == item['version']:
        existing_not_updated.append(existing.pk)
        return  # Already up-to-date

    package_version, _ = PackageVersion.objects.get_or_create(os=os, entity_package=existing, **item)
    if existing is not None:
        existing.package_version = package_version
        existing.upgradable_package = None
        existing.upgradable_version = None
        existing.upgrade_type = None
        existing.save()
    else:
        host_packages[package_version.package.name], _ = HostPackage.objects.get_or_create(
            host=host, package=package_version.package, package_version=package_version)


def _process_upgradable(host, os, host_packages, existing_upgradable_not_updated, item):
    """Process an upgradable package item."""
    existing = host_packages.get(item['name'], None)

    if existing is not None:
        if existing.upgradable_package is not None and existing.upgradable_version.version == item['version_to']:
            existing_upgradable_not_updated.append(existing.pk)
            return  # Already up-to-date

        upgradable_version, _ = PackageVersion.objects.get_or_create(
            os=os, version=item['version_to'], entity_package=existing, **item)

        if existing.package_version == upgradable_version:  # The package has been already upgraded
            existing.upgradable_package = None
            existing.upgradable_version = None
            existing.upgrade_type = None
        else:
            existing.upgradable_package = upgradable_version.package
            existing.upgradable_version = upgradable_version

        existing.save()
    else:
        installed_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_from'], **item)
        upgradable_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_to'], **item)
        HostPackage.objects.create(
            host=host, package=installed_version.package, package_version=installed_version,
            upgradable_package=upgradable_version.package, upgradable_version=upgradable_version)
