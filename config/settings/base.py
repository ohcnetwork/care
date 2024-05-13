"""
Base settings to build other settings files upon.
"""

import base64
import json
from datetime import datetime, timedelta
from pathlib import Path

import environ
from authlib.jose import JsonWebKey
from healthy_django.healthcheck.django_cache import DjangoCacheHealthCheck
from healthy_django.healthcheck.django_database import DjangoDatabaseHealthCheck

from care.utils.csp import config as csp_config
from care.utils.jwks.generate_jwk import generate_encoded_jwks
from plug_config import manager

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
APPS_DIR = BASE_DIR / "care"
env = environ.Env()

if READ_DOT_ENV_FILE := env.bool("DJANGO_READ_DOT_ENV_FILE", default=False):
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="eXZQzOzx8gV38rDG0Z0fFZWweUGl3LwMZ9aTKqJiXQTI0nKMh0Z7sbHfqT8KFEnd",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.json("DJANGO_ALLOWED_HOSTS", default=["*"])
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Asia/Kolkata"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL", default="postgres:///care")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=0)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379")

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django_filters",
    "simple_history",
    "django_ratelimit",
    "dry_rest_permissions",
    "corsheaders",
    "djangoql",
    "maintenance_mode",
    "django.contrib.postgres",
    "django_rest_passwordreset",
    "healthy_django",
]
LOCAL_APPS = [
    "care.facility",
    "care.abdm",
    "care.users",
    "care.audit_log",
    "care.hcx",
]

PLUGIN_APPS = manager.get_apps()

# Plugin Section

PLUGIN_CONFIGS = manager.get_config()

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + PLUGIN_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "care.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "/"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "/"
# https://docs.djangoproject.com/en/dev/ref/settings/#logout-redirect-url
LOGOUT_REDIRECT_URL = "/"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "care.audit_log.middleware.AuditLogMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-files
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/staticfiles/"
# https://docs.djangoproject.com/en/dev/ref/settings/#staticfiles-dirs
STATICFILES_DIRS = [str(APPS_DIR / "static")]

# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/mediafiles/"

# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-STORAGES
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}

# https://whitenoise.readthedocs.io/en/latest/django.html#WHITENOISE_MANIFEST_STRICT
WHITENOISE_MANIFEST_STRICT = False

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = env.json("CSRF_TRUSTED_ORIGINS", default=[])

# https://github.com/adamchainz/django-cors-headers#cors_allowed_origin_regexes-sequencestr--patternstr
# CORS_URLS_REGEX = r"^/api/.*$"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "EMAIL_FROM", default="Open Healthcare Network <ops@care.ohc.network>"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=False)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[Care]")

# ADMIN
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
# SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)  # noqa F405
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
# ADMINS = [("""👪""", "admin@ohc.network")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
# MANAGERS = ADMINS

# Django Admin URL.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Django Rest Framework
# ------------------------------------------------------------------------------
# https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # "rest_framework.authentication.BasicAuthentication",
        # Primary api authentication
        # "rest_framework_simplejwt.authentication.JWTAuthentication",
        "config.authentication.CustomJWTAuthentication",
        "config.authentication.CustomBasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 14,
    "SEARCH_PARAM": "search_text",
    "DEFAULT_SCHEMA_CLASS": "care.utils.schema.AutoSchema",
    "EXCEPTION_HANDLER": "config.exception_handler.exception_handler",
}

# drf-spectacular (schema generation)
# ------------------------------------------------------------------------------
# https://drf-spectacular.readthedocs.io/en/latest/settings.html
SPECTACULAR_SETTINGS = {
    "TITLE": "Care API",
    "DESCRIPTION": "Documentation of API endpoints of Care ",
    "VERSION": "1.0.0",
    # "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}

# Simple JWT (JWT Authentication)
# ------------------------------------------------------------------------------
# https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME", default=10)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_REFRESH_TOKEN_LIFETIME", default=30)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "USER_ID_FIELD": "external_id",
}

# Celery (background tasks)
# ------------------------------------------------------------------------------
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-timezone
if USE_TZ:
    # https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 1800 * 5
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 1800

# Maintenance Mode
# ------------------------------------------------------------------------------
# https://github.com/fabiocaccamo/django-maintenance-mode/tree/main#configuration-optional
MAINTENANCE_MODE = int(env("MAINTENANCE_MODE", default="0"))

#  Password Reset
# ------------------------------------------------------------------------------
# https://github.com/anexia-it/django-rest-passwordreset#configuration--settings
DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE = True
DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME = 1
# https://github.com/anexia-it/django-rest-passwordreset#custom-email-lookup
DJANGO_REST_LOOKUP_FIELD = "username"

# Hardcopy settings (pdf generation)
# ------------------------------------------------------------------------------
# https://github.com/loftylabs/django-hardcopy#installation
CHROME_WINDOW_SIZE = "2480,3508"
CHROME_PATH = "/usr/bin/chromium"

# Health Django (Health Check Config)
# ------------------------------------------------------------------------------
# https://github.com/vigneshhari/healthy_django
HEALTHY_DJANGO = [
    DjangoDatabaseHealthCheck(
        "Database", slug="main_database", connection_name="default"
    ),
    DjangoCacheHealthCheck("Cache", slug="main_cache", connection_name="default"),
]

# Audit logs
# ------------------------------------------------------------------------------
AUDIT_LOG_ENABLED = env.bool("AUDIT_LOG_ENABLED", default=False)
AUDIT_LOG = {
    "globals": {
        "exclude": {
            "applications": [
                "plain:contenttypes",
                "plain:admin",
                "plain:basehttp",
                "glob:session*",
                "glob:auth*",
                "plain:migrations",
                "plain:audit_log",
            ]
        }
    },
    "models": {
        "exclude": {
            "applications": [],
            "models": ["plain:facility.HistoricalPatientRegistration"],
            "fields": {
                "facility.PatientRegistration": [
                    "name",
                    "phone_number",
                    "emergency_phone_number",
                    "address",
                ],
                "facility.PatientExternalTest": ["name", "address", "mobile_number"],
            },
        }
    },
}

# OTP
# ------------------------------------------------------------------------------
OTP_REPEAT_WINDOW = 6  # OTPs will only be valid for 6 hours to login
OTP_MAX_REPEATS_WINDOW = 10  # times OTPs can be sent within OTP_REPEAT_WINDOW
OTP_LENGTH = 5

# ICD
# ------------------------------------------------------------------------------
ICD_SCRAPER_ROOT_CONCEPTS_URL = (
    "https://icd.who.int/browse11/l-m/en/JsonGetRootConcepts"
)
ICD_SCRAPER_CHILD_CONCEPTS_URL = (
    "https://icd.who.int/browse11/l-m/en/JsonGetChildrenConcepts"
)

# Rate Limiting
# ------------------------------------------------------------------------------
DISABLE_RATELIMIT = env.bool("DISABLE_RATELIMIT", default=False)
DJANGO_RATE_LIMIT = env("RATE_LIMIT", default="5/10m")
GOOGLE_RECAPTCHA_SECRET_KEY = env("GOOGLE_RECAPTCHA_SECRET_KEY", default="")
GOOGLE_RECAPTCHA_SITE_KEY = env("GOOGLE_RECAPTCHA_SITE_KEY", default="")
GOOGLE_CAPTCHA_POST_KEY = "g-recaptcha-response"

# SMS
# ------------------------------------------------------------------------------
USE_SMS = False

# Push Notifications
# ------------------------------------------------------------------------------
VAPID_PUBLIC_KEY = env(
    "VAPID_PUBLIC_KEY",
    default="BKNxrOpAeB_OBfXI-GlRAlw_vUVCc3mD_AkpE74iZj97twMOHXEFUeJqA7bDqGY10O-RmkvG30NaMf5ZWihnT3k",
)
VAPID_PRIVATE_KEY = env(
    "VAPID_PRIVATE_KEY", default="7mf3OFreFsgFF4jd8A71ZGdVaj8kpJdOto4cFbfAS-s"
)
SEND_SMS_NOTIFICATION = False

# Cloud and Buckets
# ------------------------------------------------------------------------------


BUCKET_PROVIDER = env("BUCKET_PROVIDER", default="aws").upper()
BUCKET_REGION = env("BUCKET_REGION", default="ap-south-1")
BUCKET_KEY = env("BUCKET_KEY", default="")
BUCKET_SECRET = env("BUCKET_SECRET", default="")
BUCKET_ENDPOINT = env("BUCKET_ENDPOINT", default="")
BUCKET_EXTERNAL_ENDPOINT = env("BUCKET_EXTERNAL_ENDPOINT", default=BUCKET_ENDPOINT)

if BUCKET_PROVIDER not in csp_config.CSProvider.__members__:
    print(f"Warning Invalid CSP Found! {BUCKET_PROVIDER}")

FILE_UPLOAD_BUCKET = env("FILE_UPLOAD_BUCKET", default="")
FILE_UPLOAD_REGION = env("FILE_UPLOAD_REGION", default=BUCKET_REGION)
FILE_UPLOAD_KEY = env("FILE_UPLOAD_KEY", default=BUCKET_KEY)
FILE_UPLOAD_SECRET = env("FILE_UPLOAD_SECRET", default=BUCKET_SECRET)
FILE_UPLOAD_BUCKET_ENDPOINT = env(
    "FILE_UPLOAD_BUCKET_ENDPOINT", default=BUCKET_ENDPOINT
)
FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT = env(
    "FILE_UPLOAD_BUCKET_EXTERNAL_ENDPOINT",
    default=BUCKET_EXTERNAL_ENDPOINT
    if BUCKET_ENDPOINT
    else FILE_UPLOAD_BUCKET_ENDPOINT,
)

ALLOWED_MIME_TYPES = env.list(
    "ALLOWED_MIME_TYPES",
    default=[
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        "image/svg+xml",
        # Videos
        "video/mp4",
        "video/mpeg",
        "video/x-msvideo",
        "video/quicktime",
        "video/x-ms-wmv",
        "video/x-flv",
        "video/webm",
        # Audio
        "audio/mpeg",
        "audio/wav",
        "audio/aac",
        "audio/ogg",
        "audio/midi",
        "audio/x-midi",
        "audio/webm",
        "audio/mp4"
        # Documents
        "text/plain",
        "text/csv",
        "application/rtf",
        "application/msword",
        "application/vnd.oasis.opendocument.text",
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.oasis.opendocument.spreadsheet",
    ],
)

FACILITY_S3_BUCKET = env("FACILITY_S3_BUCKET", default="")
FACILITY_S3_REGION = env("FACILITY_S3_REGION_CODE", default=BUCKET_REGION)
FACILITY_S3_KEY = env("FACILITY_S3_KEY", default=BUCKET_KEY)
FACILITY_S3_SECRET = env("FACILITY_S3_SECRET", default=BUCKET_SECRET)
FACILITY_S3_BUCKET_ENDPOINT = env(
    "FACILITY_S3_BUCKET_ENDPOINT", default=BUCKET_ENDPOINT
)
FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT = env(
    "FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT",
    default=BUCKET_EXTERNAL_ENDPOINT
    if BUCKET_ENDPOINT
    else FACILITY_S3_BUCKET_ENDPOINT,
)

# for setting the shifting mode
PEACETIME_MODE = env.bool("PEACETIME_MODE", default=True)

MIN_ENCOUNTER_DATE = env(
    "MIN_ENCOUNTER_DATE",
    cast=lambda d: datetime.strptime(d, "%Y-%m-%d"),
    default=datetime(2020, 1, 1),
)

# for exporting csv
CSV_REQUEST_PARAMETER = "csv"

# current hosted domain
CURRENT_DOMAIN = env("CURRENT_DOMAIN", default="localhost:8000")

# open id connect
JWKS = JsonWebKey.import_key_set(
    json.loads(base64.b64decode(env("JWKS_BASE64", default=generate_encoded_jwks())))
)

# ABDM
ENABLE_ABDM = env.bool("ENABLE_ABDM", default=False)
ABDM_CLIENT_ID = env("ABDM_CLIENT_ID", default="")
ABDM_CLIENT_SECRET = env("ABDM_CLIENT_SECRET", default="")
ABDM_URL = env("ABDM_URL", default="https://dev.abdm.gov.in")
HEALTH_SERVICE_API_URL = env(
    "HEALTH_SERVICE_API_URL", default="https://healthidsbx.abdm.gov.in/api"
)
ABDM_FACILITY_URL = env("ABDM_FACILITY_URL", default="https://facilitysbx.abdm.gov.in")
HIP_NAME_PREFIX = env("HIP_NAME_PREFIX", default="")
HIP_NAME_SUFFIX = env("HIP_NAME_SUFFIX", default="")
ABDM_USERNAME = env("ABDM_USERNAME", default="abdm_user_internal")
X_CM_ID = env("X_CM_ID", default="sbx")
FIDELIUS_URL = env("FIDELIUS_URL", default="http://fidelius:8090")

IS_PRODUCTION = False

# HCX
HCX_PROTOCOL_BASE_PATH = env(
    "HCX_PROTOCOL_BASE_PATH", default="http://staging-hcx.swasth.app/api/v0.7"
)
HCX_AUTH_BASE_PATH = env(
    "HCX_AUTH_BASE_PATH",
    default="https://staging-hcx.swasth.app/auth/realms/swasth-health-claim-exchange/protocol/openid-connect/token",
)
HCX_PARTICIPANT_CODE = env("HCX_PARTICIPANT_CODE", default="")
HCX_USERNAME = env("HCX_USERNAME", default="")
HCX_PASSWORD = env("HCX_PASSWORD", default="")
HCX_ENCRYPTION_PRIVATE_KEY_URL = env("HCX_ENCRYPTION_PRIVATE_KEY_URL", default="")
HCX_IG_URL = env("HCX_IG_URL", default="https://ig.hcxprotocol.io/v0.7.1")

PLAUSIBLE_HOST = env("PLAUSIBLE_HOST", default="")
PLAUSIBLE_SITE_ID = env("PLAUSIBLE_SITE_ID", default="")
PLAUSIBLE_AUTH_TOKEN = env("PLAUSIBLE_AUTH_TOKEN", default="")

# Disable summarization tasks
TASK_SUMMARIZE_TRIAGE = env.bool("TASK_SUMMARIZE_TRIAGE", default=True)
TASK_SUMMARIZE_TESTS = env.bool("TASK_SUMMARIZE_TESTS", default=True)
TASK_SUMMARIZE_FACILITY_CAPACITY = env.bool(
    "TASK_SUMMARIZE_FACILITY_CAPACITY", default=True
)
TASK_SUMMARIZE_PATIENT = env.bool("TASK_SUMMARIZE_PATIENT", default=True)
TASK_SUMMARIZE_DISTRICT_PATIENT = env.bool(
    "TASK_SUMMARIZE_DISTRICT_PATIENT", default=True
)
