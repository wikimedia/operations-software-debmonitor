import json
import logging

from django import http
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe

from kubernetes.models import KubernetesImage

from debmonitor.decorators import verify_clients
from debmonitor.middleware import TEXT_PLAIN
from images.models import Image


logger = logging.getLogger(__name__)


@require_safe
def index(request):
    """Kubernetes deployed images list page."""
    images = KubernetesImage.objects.all()

    table_headers = [
        {'title': 'Cluster'},
        {'title': 'Namespace'},
        {'title': 'Image name', 'tooltip':
         'Image that is deployed in the Kubernetes cluster and namespace'},
        {'title': 'OS', 'tooltip': 'Operating System that the image is running'},
        {'title': '# of containers', 'tooltip': 'Number of containers deployed'},
    ]

    args = {
        # The IDs are DataTable column IDs.
        'column_groups': [
            {'column': 0, 'title': 'Cluster', 'css_group': 1,
             'tooltip': 'Number of Images deployed to this cluster'},
            {'column': 1, 'title': 'Namespace', 'css_group': 2,
             'tooltip': 'Number of Images deployed to this namespace'},
        ],
        'default_order': json.dumps([[0, 'asc'], [1, 'asc'], [2, 'asc']]),
        'datatables_column_defs': json.dumps([
            {'targets': [0, 1], 'visible': False},
            {'targets': [0, 1], 'sortable': False},
        ]),

        'datatables_page_length': 50,
        'images': images,
        'section': 'kubernetes',
        'subtitle': '',
        'table_headers': table_headers,
        'title': 'Live Kubernetes Images',
    }
    return render(request, 'kubernetes/index.html', args)


@verify_clients
@csrf_exempt
@require_POST
def update_kubernetes_images(request):
    """Update the KubernetesImages objects from a JSON."""
    if not request.body:
        return http.HttpResponseBadRequest(f'Empty POST, expected JSON string: {request}', content_type=TEXT_PLAIN)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        return http.HttpResponseBadRequest(f'Unable to parse JSON string payload: {e}', content_type=TEXT_PLAIN)

    cluster = payload.get('cluster', '')
    if not cluster:
        return http.HttpResponseBadRequest(
            'JSON Payload missing required "cluster" key with the cluster name', content_type=TEXT_PLAIN)

    images = payload.get('images', {})
    if not isinstance(images, dict):
        return http.HttpResponseBadRequest(
            'JSON Payload key "images" is not a dictionary', content_type=TEXT_PLAIN)

    message = f'Unable to update Kubernetes images for cluster {cluster}'
    try:
        response = _update_v1(cluster, images)
    except Exception as e:  # Force a response to avoid using the HTML template for all other 500s
        logger.exception(message)
        return http.HttpResponseServerError(f'{message}: {e}', content_type=TEXT_PLAIN)
    else:
        response['success'] = False if response['missing'] or response['errors'] else True
        return http.JsonResponse(response, status=201 if response['success'] else 202)


def _update_v1(cluster, images):
    """Update API v1."""
    start_time = timezone.now()

    counter = 0
    failed = {'missing': [], 'errors': []}
    for name, data in images.items():
        try:
            image = Image.objects.get(name=name)
        except Image.DoesNotExist:
            failed['missing'].append(name)
            continue

        for namespace, containers in data.items():
            try:
                kub_image, _ = KubernetesImage.objects.update_or_create(
                    defaults={'containers': containers}, cluster=cluster, namespace=namespace, image=image)
                counter += 1
            except Exception as e:
                failed['errors'].append({'image': name, 'cluster': cluster, 'namespace': namespace, 'error': str(e)})

    logger.info(
        "Tracked %d deployed Kubernetes images for cluster '%s', skipped %d missing images and %d that errored out",
        counter,
        cluster,
        len(failed['missing']),
        len(failed['errors']),
    )

    # Delete orphaned entries based on the modification datetime for the given cluster
    res = KubernetesImage.objects.filter(cluster=cluster, modified__lt=start_time).delete()
    logger.info("Deleted %d Kubernetes images orphaned entries for cluster '%s'", res[0], cluster)
    return failed
