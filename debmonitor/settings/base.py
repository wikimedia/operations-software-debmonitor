"""
Django settings for debmonitor project.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import json
import os


# Load JSON configuration for secrets
if os.environ.get('DEBMONITOR_CONFIG', False):
    with open(os.environ.get('DEBMONITOR_CONFIG'), 'r') as config_file:
        DEBMONITOR_CONFIG = json.loads(config_file.read())
else:
    DEBMONITOR_CONFIG = {}

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
