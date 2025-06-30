import json
import logging

from collections import defaultdict

from django import http
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Count, BooleanField, Case, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe, require_POST

from bin_packages.models import PackageVersion
from debmonitor.decorators import verify_clients
from images.models import Image, ImagePackage, SECURITY_UPGRADE
from src_packages.models import OS
from debmonitor.middleware import APPLICATION_JSON, TEXT_PLAIN


logger = logging.getLogger(__name__)


@require_safe
def index(request):
    """Container image list page."""
    images = Image.objects.all()

    # Get all the additional annotations separately for query optimization purposes
    image_annotations = defaultdict(lambda: defaultdict(int))
    packages_count = Image.objects.select_related(None).values('id').annotate(
        packages_count=Count('packages', distinct=True))
    for image in packages_count:
        image_annotations[image['id']]['packages_count'] = image['packages_count']

    upgrades_count = Image.objects.select_related(None).values('id').annotate(
        upgrades_count=Count('upgradable_imagepackages', distinct=True))
    for image in upgrades_count:
        image_annotations[image['id']]['upgrades_count'] = image['upgrades_count']

    security_count = ImagePackage.objects.select_related(None).filter(upgrade_type=SECURITY_UPGRADE).values(
        'image').annotate(security_count=Count('package', distinct=True)).order_by('image')
    for image in security_count:
        image_annotations[image['image']]['security_count'] = image['security_count']

    # Insert all the annotated data back into the package objects for easy access in the templates
    for image in images:
        for annotation in ('packages_count', 'upgrades_count', 'security_count'):
            setattr(image, annotation, image_annotations[image.id][annotation])

    table_headers = [
        {'title': 'Image name', 'badges': [
         {'style': 'primary', 'tooltip': 'Number of packages installed in this image'},
         {'style': 'warning', 'tooltip': 'Number of packages pending an upgrade in this image'},
         {'style': 'danger', 'tooltip': 'Number of packages pending a security upgrade in this image'}]},
        {'title': 'OS', 'tooltip': 'Operating System that the image is running'},
        {'title': 'Last update', 'tooltip': 'Last time the image data was updated'},
        {'title': '# Packages', 'tooltip': 'Number of package which the image has installed'},
        {'title': '# Upgrades'},
        {'title': '# Security Upgrades'},
        {'title': 'Last update timestamp'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'custom_sort': {'name': 'Imagename', 'installed': 3, 'upgrades': 4, 'security': 5},
        'datatables_column_defs': json.dumps([
            {'targets': [3, 4, 5, 6], 'visible': False},
            {'targets': [2], 'orderData': [6]},
            {'targets': [2, 3, 4, 5, 6], 'searchable': False},
        ]),

        'datatables_page_length': 50,
        'images': images,
        'section': 'images',
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Images',
    }
    return render(request, 'images/index.html', args)


class DetailView(View):

    @method_decorator(verify_clients(['DELETE']))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, name):
        """Image detail page."""
        image = get_object_or_404(Image, name=name)
        if request.META.get('HTTP_ACCEPT', '') == APPLICATION_JSON:
            return http.JsonResponse(image.to_dict())

        total_instances = sum(instance.instances for instance in image.instances.all())
        image_packages = ImagePackage.objects.filter(image=image).annotate(
            has_upgrade=Case(
                When(upgradable_imageversion__isnull=False, then=True),
                default=False,
                output_field=BooleanField())
            ).order_by('-has_upgrade', '-upgrade_type', 'package__name')

        table_headers = [
            {'title': 'Package', 'tooltip': 'Name of the binary package'},
            {'title': 'Version', 'tooltip': 'Installed version of this binary package'},
            {'title': 'Upgradable to', 'tooltip': 'Version of this binary package the image can upgrade to'},
            {'title': 'Upgrade Type'},
        ]

        args = {
            'datatables_column_defs': json.dumps(
                [{'targets': [3], 'visible': False}, {'targets': [1, 2], 'orderable': False}]),
            'datatables_page_length': -1,
            'external_links': {
                key: value.format(fqdn=image.name, image_path=image.name.split('/', 1)[1].rsplit(':', 1)[0])
                for key, value in settings.DEBMONITOR_IMAGE_EXTERNAL_LINKS.items()
            },
            'image': image,
            'image_packages': image_packages,
            'section': 'images',
            'subtitle': 'Image',
            'table_headers': table_headers,
            'title': image.name,
            'total_instances': total_instances,
            'upgrades_column': 2,
        }
        return render(request, 'images/detail.html', args)

    def delete(self, request, name):
        image = get_object_or_404(Image, name=name)
        image.delete()

        return http.HttpResponse(status=204, content_type=TEXT_PLAIN)


@verify_clients
@csrf_exempt
@require_POST
def update_image(request, name):
    """Update an image record and all it's related information from a JSON."""
    if not request.body:
        return http.HttpResponseBadRequest("Empty POST, expected JSON string: {req}".format(
            req=request), content_type=TEXT_PLAIN)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        return http.HttpResponseBadRequest(
            'Unable to parse JSON string payload: {e}'.format(e=e), content_type=TEXT_PLAIN)

    if not payload.get('update_type', ''):
        return http.HttpResponseBadRequest("Update type not specificed in passed parameters match",
                                           content_type=TEXT_PLAIN)

    if name != payload.get('image_name', ''):
        return http.HttpResponseBadRequest("URL image '{name}' and POST payload image name '{image}'"
                                           "do not match".format(name=name, image=payload.get('image_name', '')),
                                           content_type=TEXT_PLAIN)
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

    message = "Unable to update image '{image}'".format(image=name)
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
    start_time = timezone.now()

    try:
        im = Image.objects.get(name=name)
        im.os = os
        im.save()  # Always update at least the modification time
        image_packages = {image_pkg.package.name: image_pkg for image_pkg in ImagePackage.objects.filter(image=im)}

    except Image.DoesNotExist:
        im = Image(name=name, os=os)
        im.save()
        image_packages = {}
        logger.info("Created image '%s'", name)

    existing_not_updated = []
    existing_upgradable_not_updated = []

    installed = payload.get('installed', [])
    for item in installed:
        _process_installed(im, os, image_packages, existing_not_updated, item)

    logger.info("Tracked %d installed packages for image '%s'", len(installed), name)

    uninstalled = payload.get('uninstalled', [])
    for item in uninstalled:
        existing = image_packages.get(item['name'], None)
        if existing is not None:
            existing.delete()

    logger.info("Untracked %d uninstalled packages for image '%s'", len(uninstalled), name)

    upgradable = payload.get('upgradable', [])
    for item in upgradable:
        _process_upgradable(im, os, image_packages, existing_upgradable_not_updated, item)

    logger.info("Tracked %d upgradable packages for image '%s'", len(upgradable), name)

    if payload['update_type'] == 'full':
        _garbage_collection(im, name, start_time, existing_not_updated, existing_upgradable_not_updated)


def _garbage_collection(image, name, start_time, existing_not_updated, existing_upgradable_not_updated):
    # Delete orphaned entries based on the modification datetime and the list of already up-to-date IDs
    res = ImagePackage.objects.filter(image=image,
                                      modified__lt=start_time).exclude(pk__in=existing_not_updated).delete()
    logger.info("Deleted %d ImagePackage orphaned entries for image '%s'", res[0], name)

    # Cleanup orphaned upgrades based on the modification datetime and the list of already up-to-date IDs
    image_packages = ImagePackage.objects.filter(
        image=image, modified__lt=start_time, upgradable_imagepackage__isnull=False).exclude(
        pk__in=existing_upgradable_not_updated)

    for image_package in image_packages:
        image_package.upgradable_imagepackage = None
        image_package.upgradable_imageversion = None
        image_package.upgrade_type = None
        image_package.save()

    logger.info("Cleaned %d ImagePackage upgradable info for image '%s'", len(image_packages), name)


def _process_installed(image, os, image_packages, existing_not_updated, item):
    """Process an installed package item, return True if it was created or updated."""
    existing = image_packages.get(item['name'], None)

    if existing is not None and existing.package_version.version == item['version']:
        existing_not_updated.append(existing.pk)
        return  # Already up-to-date

    package_version, _ = PackageVersion.objects.get_or_create(os=os, entity_package=existing, **item)
    if existing is not None:
        existing.package_version = package_version
        existing.upgradable_imagepackage = None
        existing.upgradable_imageversion = None
        existing.upgrade_type = None
        existing.save()
    else:
        image_packages[package_version.package.name] = ImagePackage.objects.create(
            image=image, package=package_version.package, package_version=package_version)


def _process_upgradable(image, os, image_packages, existing_upgradable_not_updated, item):
    """Process an upgradable package item."""
    existing = image_packages.get(item['name'], None)

    if existing is not None:
        if (existing.upgradable_imagepackage is not None and
                existing.upgradable_imageversion.version == item['version_to']):
            existing_upgradable_not_updated.append(existing.pk)
            return  # Already up-to-date

        upgradable_version, _ = PackageVersion.objects.get_or_create(
            os=os, version=item['version_to'], entity_package=existing, **item)

        if existing.package_version == upgradable_version:  # The package has been already upgraded
            existing.upgradable_imagepackage = None
            existing.upgradable_imageversion = None
            existing.upgrade_type = None
        else:
            existing.upgradable_imagepackage = upgradable_version.package
            existing.upgradable_imageversion = upgradable_version

        existing.save()
    else:
        installed_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_from'], **item)
        upgradable_version, _ = PackageVersion.objects.get_or_create(os=os, version=item['version_to'], **item)
        ImagePackage.objects.create(
            image=image, package=installed_version.package, package_version=installed_version,
            upgradable_imagepackage=upgradable_version.package, upgradable_imageversion=upgradable_version)
