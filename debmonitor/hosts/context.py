from hosts.models import SECURITY_UPGRADE


def security_upgrade(request):
    """Expose the security upgrade constant to the templates."""
    return {'security_upgrade': SECURITY_UPGRADE}
