import json

from django.shortcuts import render
from django.views.decorators.http import require_safe

from kubernetes.models import KubernetesImage


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
