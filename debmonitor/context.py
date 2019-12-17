from django.conf import settings


def search_min_length(request):
    """Expose the minimum search length required for the search input."""
    return {'SEARCH_MIN_LENGTH': settings.DEBMONITOR_SEARCH_MIN_LENGTH}
