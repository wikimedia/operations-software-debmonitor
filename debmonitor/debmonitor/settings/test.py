from django.core.management.utils import get_random_secret_key

from debmonitor.settings.base import *  # noqa: F403 unable to detect undefined names


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: use a separate secret key for testing or let it autogenerate one each time
SECRET_KEY = DEBMONITOR_CONFIG.get('SECRET_KEY', get_random_secret_key())  # noqa F405 defined from star imports

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging
LOGGING['handlers']['console']['level'] = 'DEBUG'  # noqa F405 defined from star imports
LOGGING['loggers'][''] = {  # noqa F405 defined from star imports
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

if DEBMONITOR_CONFIG.get('LDAP', {}):  # noqa F405 defined from star imports
    if 'django_auth_ldap' in LOGGING['loggers']:  # noqa F405 defined from star imports
        LOGGING['loggers']['django_auth_ldap']['level'] = 'DEBUG'  # noqa F405 defined from star imports
