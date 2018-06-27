import re

from django.conf import settings


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


class HostAuthError(Exception):
    """Raised when an host is not authorized to perform an operation."""


def is_valid_cn(dn, name):
    """Return True the provided Distinguished Name is allowed to modify the data for the provided name."""
    parsed_dn = DN_PARSE_PATTERN.search(dn)
    if parsed_dn is None:
        return False

    cn = parsed_dn.group('cn')
    if cn == name or cn in settings.DEBMONITOR_PROXY_HOSTS:
        return True

    return False


def verify_clients(request, hostname=None):
    """Verify the client certificate and optionally its hostname.

    Raises: HostAuthError on failure
    """
    if not settings.DEBMONITOR_VERIFY_CLIENTS:
        return

    ssl_verify = request.META.get(SSL_CLIENT_VERIFY_HEADER, '')
    if ssl_verify != SSL_CLIENT_VERIFY_SUCCESS:  # Verify that the client has a valid certificate
        raise HostAuthError("Client certificate validation failed: '{message}'".format(
            message=ssl_verify))

    if hostname is None:  # Nothing else to verify
        return

    # Verify that the hostname in the certificate DN matches the given hostname from the URI
    ssl_dn = request.META.get(SSL_CLIENT_SUBJECT_DN_HEADER, '')
    if not is_valid_cn(ssl_dn, hostname):
        raise HostAuthError("Unauthorized to update host '{name}' with certificate '{dn}'".format(
            name=hostname, dn=ssl_dn))
