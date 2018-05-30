"""
Django settings for debmonitor project.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import json
import os
import sys


# Load JSON configuration for secrets
if os.environ.get('DEBMONITOR_CONFIG', False):
    with open(os.environ.get('DEBMONITOR_CONFIG'), 'r') as config_file:
        DEBMONITOR_CONFIG = json.loads(config_file.read())
else:
    DEBMONITOR_CONFIG = {}

# Debmonitor custom configuration
DEBMONITOR_VERIFY_CLIENTS = DEBMONITOR_CONFIG.get('VERIFY_CLIENTS', True)
DEBMONITOR_PROXY_HOSTS = DEBMONITOR_CONFIG.get('PROXY_HOSTS', [])

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Quick-start development settings - unsuitable for production

ALLOWED_HOSTS = DEBMONITOR_CONFIG.get('ALLOWED_HOSTS', [])

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bin_packages',
    'hosts',
    'src_packages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBMONITOR_CONFIG.get('REQUIRE_LOGIN', False):
    # Enforce login for every view
    INSTALLED_APPS.append('stronghold')
    MIDDLEWARE.append('stronghold.middleware.LoginRequiredMiddleware')

ROOT_URLCONF = 'debmonitor.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hosts.context.security_upgrade',
            ],
        },
    },
]

WSGI_APPLICATION = 'debmonitor.wsgi.application'

# Database

if DEBMONITOR_CONFIG.get('MYSQL', {}):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DEBMONITOR_CONFIG['MYSQL']['DB_NAME'],
            'USER': DEBMONITOR_CONFIG['MYSQL']['DB_USER'],
            'PASSWORD': DEBMONITOR_CONFIG['MYSQL']['DB_PASSWORD'],
            'HOST': DEBMONITOR_CONFIG['MYSQL']['DB_HOST'],
            'PORT': DEBMONITOR_CONFIG['MYSQL']['DB_PORT'],
            'OPTIONS': DEBMONITOR_CONFIG['MYSQL']['OPTIONS'],
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        },
    }

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = LOGIN_URL

# Security

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Internationalization

USE_I18N = False
USE_L10N = False
USE_TZ = True
TIME_ZONE = DEBMONITOR_CONFIG.get('TIME_ZONE', 'UTC')

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = DEBMONITOR_CONFIG.get('STATIC_ROOT', os.path.join(BASE_DIR, os.pardir, 'static'))
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Logging

LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',  # logging handler that outputs log messages to terminal
            'level': 'INFO',  # message level to be written to console
        },
    },
    'loggers': {},
}

if DEBMONITOR_CONFIG.get('LOG_DB_QUERIES', False):
    LOGGING['loggers']['django.db'] = {
        'level': 'DEBUG',
    }

# LDAP, dynamically load all overriden variables from the config

if DEBMONITOR_CONFIG.get('LDAP', {}):
    import ldap

    from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

    AUTHENTICATION_BACKENDS = ('django_auth_ldap.backend.LDAPBackend',)
    LOGGING['loggers']['django_auth_ldap'] = {
        'handlers': ['console'],
        'level': 'INFO',
    }

    module = sys.modules[__name__]
    for key, value in DEBMONITOR_CONFIG.get('LDAP', {}).items():
        if key == 'GROUP_SEARCH':
            AUTH_LDAP_GROUP_SEARCH = LDAPSearch(value, ldap.SCOPE_SUBTREE, '(objectClass=groupOfNames)')
            AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
        elif key == 'USER_SEARCH':
            AUTH_LDAP_USER_SEARCH = LDAPSearch(
                value['SEARCH'],
                ldap.SCOPE_ONELEVEL,
                '({user_field}=%(user)s)'.format(user_field=value['USER_FIELD']))
        else:
            setattr(module, 'AUTH_LDAP_' + key, value)
