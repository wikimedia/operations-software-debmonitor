import re

from django.conf import settings
from django.http import HttpResponseForbidden


# String to use to check if the web server has verified the client certificate.
# Nginx sets the $ssl_client_verify variable to NONE, SUCCESS, FAILED:reason.
# Apache sets the environmental variable SSL_CLIENT_VERIFY to NONE, SUCCESS, GENEROUS or FAILED:reason.
SSL_CLIENT_VERIFY_SUCCESS = 'SUCCESS'
# HTTP header that holds the client's certificate validation result as reported by the web server.
SSL_CLIENT_VERIFY_HEADER = 'HTTP_X_CLIENT_CERT_VERIFY'
# HTTP header that holds the client's certificate DN as reported by the web browser
# (i.e. $ssl_client_s_dn for Nginx and SSL_CLIENT_S_DN for Apache).
SSL_CLIENT_SUBJECT_DN_HEADER = 'HTTP_X_CLIENT_CERT_SUBJECT_DN'
# Given that the expected CN is a hostname and the limited scope of this check, a quick regex approach was preferred
# compared to requiring an LDAP library just to parse the DN.
DN_PARSE_PATTERN = re.compile('(^|,)CN=(?P<cn>[^,]+)(,|$)', re.I)
TEXT_PLAIN = 'text/plain'


def get_host_cn(dn):
    """Extract the Common Name from the given Distinguished Name."""
    parsed_dn = DN_PARSE_PATTERN.search(dn)
    if parsed_dn is None:
        return

    return parsed_dn.group('cn')


def is_valid_cn(cn, name):
    """Return True if the provided Common Name is allowed to modify the data for the provided host.
    This is the case if the CN matches the package hostname or if it's coming from a valid proxy
    for host submisions  """
    if cn == name or cn in settings.DEBMONITOR_PROXY_HOSTS:
        return True

    return False


def is_valid_image_proxy(cn):
    """Return True if the provided CN is in the list of valid proxies for image submissions."""
    if cn in settings.DEBMONITOR_PROXY_IMAGES:
        return True

    return False


class AuthHost(object):
    """Authenticated host object, to be used as a 'fake' User."""

    is_authenticated = True

    def __init__(self, hostname):
        """Initialize the hostname of the Host."""
        self.hostname = hostname


class AuthHostMiddleware(object):
    """Middleware to authenticate the client hosts, when needed."""

    def __init__(self, get_response):
        """Required by Django API."""
        self.get_response = get_response

    def __call__(self, request):
        """Required by Django API."""
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Authenticate the client's certificate."""
        if not settings.DEBMONITOR_VERIFY_CLIENTS:
            return

        verify_clients = getattr(view_func, 'debmonitor_verify_clients', False)
        verify_clients_methods = getattr(view_func, 'debmonitor_verify_clients_methods', [])
        if not verify_clients and request.method not in verify_clients_methods:
            return

        ssl_verify = request.META.get(SSL_CLIENT_VERIFY_HEADER, '')
        if ssl_verify != SSL_CLIENT_VERIFY_SUCCESS:  # Verify that the client has a valid certificate
            return HttpResponseForbidden("Client certificate validation failed: '{message}'".format(
                message=ssl_verify), content_type=TEXT_PLAIN)

        ssl_dn = request.META.get(SSL_CLIENT_SUBJECT_DN_HEADER, '')
        cn = get_host_cn(ssl_dn)
        request.user = AuthHost(cn)

        if view_kwargs.get('name', None) is None:  # Nothing else to verify
            return

        # For image submissions we don't validate the host name, but only whether the image data
        # is submitted from a valid proxy host
        if view_func.__name__ == 'update_image':
            if not is_valid_image_proxy(cn):
                return HttpResponseForbidden("Unauthorized to modify image '{name}' with certificate '{dn}'".format(
                    name=view_kwargs['name'], dn=ssl_dn), content_type=TEXT_PLAIN)

        else:
            # Verify that the hostname in the certificate DN matches the given hostname from the URI
            if not is_valid_cn(cn, view_kwargs['name']):
                return HttpResponseForbidden("Unauthorized to modify host '{name}' with certificate '{dn}'".format(
                    name=view_kwargs['name'], dn=ssl_dn), content_type=TEXT_PLAIN)
