"""
Base settings to build other settings files upon.
"""

import json
from datetime import timedelta

import environ
from healthy_django.healthcheck.celery_queue_length import DjangoCeleryQueueLengthHealthCheck
from healthy_django.healthcheck.django_cache import DjangoCacheHealthCheck
from healthy_django.healthcheck.django_database import DjangoDatabaseHealthCheck

from care.utils.csp import config as csp_config

ROOT_DIR = environ.Path(__file__) - 3  # (care/config/settings/base.py - 3 = care/)
APPS_DIR = ROOT_DIR.path("care")

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(".env")))

# GENERAL
# ------------------------------------------------------------------------------
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
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [ROOT_DIR.path("locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL", default="postgres:///care")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASES["default"]["CONN_MAX_AGE"] = 300

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# CollectFast
#

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    # "django.contrib.gis",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "storages",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_yasg",
    "drf_extra_fields",
    "django_filters",
    "simple_history",
    "ratelimit",
    "dry_rest_permissions",
    "corsheaders",
    "watchman",
    "djangoql",
    "maintenance_mode",
    "django.contrib.postgres",
    "django_celery_beat",
    "django_rest_passwordreset",
    "healthy_django",
]

LOCAL_APPS = ["care.users.apps.UsersConfig", "care.facility", "care.audit_log.apps.AuditLogConfig"]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "care.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_FORMS = {"signup": "users.forms.CustomSignupForm"}

# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "/users/signin"

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
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
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
USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

STATIC_URL = "/staticfiles/"
STATIC_ROOT = str(ROOT_DIR("staticfiles"))
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MANIFEST_STRICT = False

STATICFILES_DIRS = [str(APPS_DIR.path("static"))]

MEDIA_URL = "/mediafiles/"
MEDIA_ROOT = str(APPS_DIR("media"))

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("templates"))],
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
                "care.utils.context_processors.settings_context",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = json.loads(env("CSRF_TRUSTED_ORIGINS", default="[]"))

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
# https://docs.djangoproject.com/en/2.2/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""👪""", "admin@coronasafe.in")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s " "%(process)d %(thread)d %(message)s"}
    },
    "handlers": {"console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "verbose",}},
    "root": {"level": "INFO", "handlers": ["console"]},
}

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "care.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "care.users.adapters.SocialAccountAdapter"

# Django Rest Framework
# ------------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # "rest_framework.authentication.BasicAuthentication",
        # Primary api authentication
        # "rest_framework_simplejwt.authentication.JWTAuthentication",
        "config.authentication.CustomJWTAuthentication",
        "config.authentication.CustomBasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 14,
    "SEARCH_PARAM": "search_text",
}

# Your stuff...
# ------------------------------------------------------------------------------


ACCOUNT_EMAIL_VERIFICATION = False
LOGOUT_REDIRECT_URL = "/"
STAFF_ACCOUNT_TYPE = 10

# Simple JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_TOKEN_LIFETIME", default=10)),
    "REFRESH_TOKEN_LIFETIME": timedelta(minutes=env("JWT_REFRESH_TOKEN_LIFETIME", default=30)),
    "ROTATE_REFRESH_TOKENS": True,
}

# LOCATION_FIELD = {
#     "search.provider": "google",
#     "map.provider": "openstreetmap",
#     "provider.openstreetmap.max_zoom": 18,
# }


def GETKEY(group, request):
    return "ratelimit"


DJANGO_RATE_LIMIT = env("RATE_LIMIT", default="5/10m")

GOOGLE_RECAPTCHA_SECRET_KEY = env("GOOGLE_RECAPTCHA_SECRET_KEY", default="")

GOOGLE_RECAPTCHA_SITE_KEY = env("GOOGLE_RECAPTCHA_SITE_KEY", default="")

GOOGLE_CAPTCHA_POST_KEY = "g-recaptcha-response"

CORS_ORIGIN_ALLOW_ALL = True

MAINTENANCE_MODE = int(env("MAINTENANCE_MODE", default="0"))

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 1800 * 5
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 1800
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
# CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseSc:wqheduler"
CELERY_TIMEZONE = "Asia/Kolkata"

CSV_REQUEST_PARAMETER = "csv"

DEFAULT_FROM_EMAIL = env("EMAIL_FROM", default="Coronasafe network <care@coronasafe.network>")

CURRENT_DOMAIN = env("CURRENT_DOMAIN", default="localhost:8000")

DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE = True

DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME = 1

DJANGO_REST_LOOKUP_FIELD = "username"

CHROME_WINDOW_SIZE = "2480,3508"

CHROME_PATH = "/usr/bin/google-chrome-stable"

IS_PRODUCTION = False

OTP_REPEAT_WINDOW = 6  # Otps will only be valid for 6 hours to login

OTP_MAX_REPEATS_WINDOW = 10  # can only send this many OTP's in current OTP_REPEAT_WINDOW

OTP_LENGTH = 5

# SMS
USE_SMS = False

DEFAULT_VAPID_PUBLIC_KEY = "BKNxrOpAeB_OBfXI-GlRAlw_vUVCc3mD_AkpE74iZj97twMOHXEFUeJqA7bDqGY10O-RmkvG30NaMf5ZWihnT3k"

DEFAULT_VAPID_PRIVATE_KEY = "7mf3OFreFsgFF4jd8A71ZGdVaj8kpJdOto4cFbfAS-s"

VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default=DEFAULT_VAPID_PUBLIC_KEY)
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default=DEFAULT_VAPID_PRIVATE_KEY)

#######################
# File Upload Parameters

FILE_UPLOAD_BUCKET = env("FILE_UPLOAD_BUCKET", default="")
# FILE_UPLOAD_REGION = env("FILE_UPLOAD_REGION", default="care-patient-staging")
FILE_UPLOAD_KEY = env("FILE_UPLOAD_KEY", default="")
FILE_UPLOAD_SECRET = env("FILE_UPLOAD_SECRET", default="")
FILE_UPLOAD_BUCKET_ENDPOINT = env("FILE_UPLOAD_BUCKET_ENDPOINT", default=f"https://{FILE_UPLOAD_BUCKET}.s3.amazonaws.com")

FACILITY_S3_BUCKET = env("FACILITY_S3_BUCKET", default="")
FACILITY_S3_KEY = env("FACILITY_S3_KEY", default="")
FACILITY_S3_SECRET = env("FACILITY_S3_SECRET", default="")
FACILITY_S3_BUCKET_ENDPOINT = env("FACILITY_S3_BUCKET_ENDPOINT", default=f"https://{FACILITY_S3_BUCKET}.s3.amazonaws.com")


# Audit logs
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
                "facility.PatientRegistration": ["name", "phone_number", "emergency_phone_number", "address"],
                "facility.PatientExternalTest": ["name", "address", "mobile_number"],
            },
        }
    },
}

SEND_SMS_NOTIFICATION = False

# Whatsapp Integrations
ENABLE_WHATSAPP = env.bool("ENABLE_WHATSAPP", default=False)
WHATSAPP_API_ENDPOINT = env("WHATSAPP_API_ENDPOINT", default="")
WHATSAPP_API_USERNAME = env("WHATSAPP_API_USERNAME", default="")
WHATSAPP_API_PASSWORD = env("WHATSAPP_API_PASSWORD", default="")
WHATSAPP_ENCRYPTION_KEY = env("WHATSAPP_ENCRYPTION_KEY", default="")
WHATSAPP_MESSAGE_CONFIG = env("WHATSAPP_MESSAGE_CONFIG", default=None)

DISABLE_RATELIMIT = False

ENABLE_ADMIN_REPORTS = env.bool("ENABLE_ADMIN_REPORTS", default=False)

# Health Check Config

default_configuration = [
    DjangoDatabaseHealthCheck("Database", slug="main_database", connection_name="default"),
    DjangoCacheHealthCheck("Cache", slug="main_cache", connection_name="default"),
    DjangoCeleryQueueLengthHealthCheck(
        "Celery Queue Length",
        slug="celery_queue",
        broker=CELERY_BROKER_URL,
        queue_name="celery",
        info_length=10,
        warning_length=20,
        alert_length=30,
    ),
]
HEALTHY_DJANGO = default_configuration


CLOUD_PROVIDER = env("CLOUD_PROVIDER", default="aws").upper()

CLOUD_REGION = env("CLOUD_REGION", default="ap-south-1")

if CLOUD_PROVIDER not in csp_config.CSProvider.__members__:
    print(f"Warning Invalid CSP Found! {CLOUD_PROVIDER}")
