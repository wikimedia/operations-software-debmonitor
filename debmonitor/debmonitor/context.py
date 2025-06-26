from django.conf import settings


def search_min_length(request):
    """Expose the minimum search length required for the search input."""
    return {'SEARCH_MIN_LENGTH': settings.DEBMONITOR_SEARCH_MIN_LENGTH}


def javascript_storage(request):
    """Return where JavaScript/CSS is fetched from."""
    return {'JAVASCRIPT_STORAGE': settings.DEBMONITOR_JAVASCRIPT_STORAGE}
