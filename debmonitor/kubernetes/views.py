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
        {'title': 'Instances', 'tooltip': 'Number of instances deployed'},
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
    message = f'Unable to update Kubernetes images for cluster {cluster}'
    try:
        _update_v1(request, cluster, images)
    except (KeyError, TypeError, ValueError, Image.DoesNotExist) as e:
        logger.exception(message)
        return http.HttpResponseBadRequest(f'{message}: {e}', content_type=TEXT_PLAIN)
    except Exception as e:  # Force a response to avoid using the HTML template for all other 500s
        logger.exception(message)
        return http.HttpResponseServerError(f'{message}: {e}', content_type=TEXT_PLAIN)
    else:
        return http.HttpResponse(status=201, content_type=TEXT_PLAIN)


def _update_v1(request, cluster, images):
    """Update API v1."""
    start_time = timezone.now()

    counter = 0
    for name, data in images.items():
        image = Image.objects.get(name=name)
        for namespace, instances in data.items():
            kub_image, _ = KubernetesImage.objects.update_or_create(
                defaults={'instances': instances}, cluster=cluster, namespace=namespace, image=image)
            counter += 1

    logger.info("Tracked %d deployed Kubernetes images for cluster '%s'", counter, cluster)

    # Delete orphaned entries based on the modification datetime for the given cluster
    res = KubernetesImage.objects.filter(cluster=cluster, modified__lt=start_time).delete()
    logger.info("Deleted %d Kubernetes images orphaned entries for cluster '%s'", res[0], cluster)
