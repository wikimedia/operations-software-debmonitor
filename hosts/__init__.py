import re

from django.conf import settings


# Given that the expected CN is a hostname and the limited scope of this check, a quick regex approach was preferred
# compared to requiring an LDAP library just to parse the DN.
DN_PARSE_PATTERN = re.compile('(^|,)CN=(?P<cn>[^,]+)(,|$)', re.I)


def is_valid_cn(dn, name):
    """Return True the provided Distinguished Name is allowed to modify the data for the provided name."""
    parsed_dn = DN_PARSE_PATTERN.search(dn)
    if parsed_dn is None:
        return False

    cn = parsed_dn.group('cn')
    if cn == name or cn in settings.DEBMONITOR_PROXY_HOSTS:
        return True

    return False
