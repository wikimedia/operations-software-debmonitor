from debmonitor.settings.base import *  # noqa: F403 unable to detect undefined names


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = DEBMONITOR_CONFIG['SECRET_KEY']  # noqa F405 defined from star imports

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = (
    DEBMONITOR_CONFIG.get('SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO'),  # noqa F405 defined from star imports
    'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
