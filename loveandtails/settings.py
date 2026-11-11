"""
Django settings for the Love and Tails backend.

All environment-specific values are read from environment variables
(or a local `.env` file). See `.env.example` for the full list.
"""

from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')


# Core

SECRET_KEY = env('DJANGO_SECRET_KEY')

DEBUG = env.bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Render sets this to the service's *.onrender.com hostname.
if RENDER_EXTERNAL_HOSTNAME := env('RENDER_EXTERNAL_HOSTNAME', default=''):
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

# Use a non-obvious path in production to cut down on automated admin login attempts.
ADMIN_URL = env('DJANGO_ADMIN_URL', default='admin/')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    # Local
    'apps.core',
    'apps.users',
    'apps.waitlist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'loveandtails.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'loveandtails.wsgi.application'


# Database (PostgreSQL)

DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default='postgres://loveandtails:loveandtails@localhost:5432/loveandtails',
    ),
}
DATABASES['default']['CONN_MAX_AGE'] = env.int('DATABASE_CONN_MAX_AGE', default=60)
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Cache (Redis). Shared by all server processes, so per-IP rate limits hold across workers.

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'KEY_PREFIX': 'loveandtails',
    },
}


# Authentication

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static and media files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Served by WhiteNoise (compressed, with cache-busting hashed filenames). Run collectstatic on deploy.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Email
# Without EMAIL_HOST, emails are printed to the console instead of sent.

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Love and Tails <noreply@localhost>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

if env('EMAIL_HOST', default=''):
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {
                'host': env('EMAIL_HOST'),
                'port': env.int('EMAIL_PORT', default=587),
                'username': env('EMAIL_HOST_USER', default=''),
                'password': env('EMAIL_HOST_PASSWORD', default=''),
                'use_tls': env.bool('EMAIL_USE_TLS', default=True),
                'timeout': env.int('EMAIL_TIMEOUT', default=10),
            },
        },
    }
else:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.console.EmailBackend',
        },
    }

# Off until a real email provider is configured. Signups are still saved with an empty
# confirmation_sent_at, so they can be emailed later from the admin.
WAITLIST_CONFIRMATION_EMAILS = env.bool(
    'WAITLIST_CONFIRMATION_EMAILS', default=bool(env('EMAIL_HOST', default=''))
)


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # JSON only in production; the clickable HTML "browsable API" is a dev convenience.
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        *(['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttling.AnonRateThrottle',
        'apps.core.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Safety net for every endpoint: per IP when logged out, per user when logged in.
        'anon': '60/minute',
        'user': '300/minute',
        # Per IP. Slows down password guessing.
        'login': '10/minute',
        # Per IP. Limits spam account creation.
        'register': '10/hour',
        # Public endpoint that sends email: cap per IP to prevent abuse.
        'waitlist': '10/hour',
    },
    # Number of reverse proxies / load balancers in front of the app, used to find the
    # client IP for rate limiting. Unset trusts the client's X-Forwarded-For header as-is.
    'NUM_PROXIES': env.int('NUM_PROXIES', default=None),
}


# JWT (used by the mobile and web clients)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_MINUTES', default=30)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_DAYS', default=30)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    # Tokens carry a hash of the user's password, so changing the password logs out every device.
    'CHECK_REVOKE_TOKEN': True,
    'TOKEN_REFRESH_SERIALIZER': 'apps.users.serializers.TokenRefreshSerializer',
}


# CORS (web app origins; native mobile apps are not subject to CORS)

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_URLS_REGEX = r'^/api/.*$'
# JWTs travel in the Authorization header, so cross-origin cookies aren't needed.
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=False)


# OpenAPI / Swagger docs
# Public in development. In production only staff can view them (log in at the admin first).

API_DOCS_PUBLIC = env.bool('API_DOCS_PUBLIC', default=DEBUG)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Love and Tails API',
    'DESCRIPTION': 'Backend API for the Love and Tails mobile and web applications.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['apps.core.permissions.CanViewAPIDocs'],
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+',
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayOperationId': False,
    },
}


# Logging
# Everything goes to stdout so the hosting platform collects it. Without this, Django drops
# warnings and errors (including security events such as DisallowedHost) when DEBUG is off.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'default'},
    },
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
    'loggers': {
        'django': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO'), 'propagate': False},
    },
}


# Tests

TEST_RUNNER = 'apps.core.test_runner.TestRunner'


# Production security

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
    # Platform health checks may call over plain HTTP; answer them instead of redirecting.
    SECURE_REDIRECT_EXEMPT = [r'^api/v1/health/']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('DJANGO_SECURE_HSTS_SECONDS', default=60)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
