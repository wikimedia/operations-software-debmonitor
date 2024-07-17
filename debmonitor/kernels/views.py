import json

from django import http
from django.db.models import Count, Prefetch
from django.shortcuts import render
from django.views.decorators.http import require_safe

from hosts.models import Host
from kernels.models import KernelVersion


@require_safe
def index(request):
    """Kernels list page."""
    kernels = KernelVersion.objects.annotate(hosts_count=Count('hosts'))

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
def detail(request, os_id, slug):
    """Kernel detail page."""
    kernel = KernelVersion.objects.filter(os__id=os_id, slug=slug).prefetch_related(
        Prefetch('hosts', queryset=Host.objects.all().select_related(None)))

    if len(kernel) != 1:
        raise http.Http404

    args = {
        'datatables_page_length': 50,
        'kernel': kernel[0],
        'section': 'kernels',
        'subtitle': 'Kernel',
        'table_headers': [{'title': 'Hostname'}],
        'title': kernel[0].name,
    }
    return render(request, 'kernels/detail.html', args)
