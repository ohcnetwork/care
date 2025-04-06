import base64
import json
import logging

import sentry_sdk
from authlib.jose import JsonWebKey
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from sentry_sdk.integrations.redis import RedisIntegration

from care.utils.jwks.generate_jwk import get_jwks_from_file

from .base import *  # noqa
from .base import APP_VERSION, DATABASES, TEMPLATES, env

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"] = env.db("DATABASE_URL")
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)
# https://github.com/adamchainz/django-cors-headers#cors_allowed_origins-sequencestr
CORS_ALLOWED_ORIGINS = env.json("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOWED_ORIGIN_REGEXES = env.json("CORS_ALLOWED_ORIGIN_REGEXES", default=[])

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[-1]["OPTIONS"]["loaders"] = [  # type: ignore[index]
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_USE_TLS = True

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
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
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
    },
}

# Sentry
# ------------------------------------------------------------------------------
# https://docs.sentry.io/platforms/python/guides/django/configuration/
if SENTRY_DSN := env("SENTRY_DSN", default=""):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=APP_VERSION,
        environment=env("SENTRY_ENVIRONMENT", default="deployment-unknown"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0),
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0),
        integrations=[
            LoggingIntegration(
                event_level=env.int("SENTRY_EVENT_LEVEL", default=logging.ERROR)
            ),
            DjangoIntegration(),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
        ],
    )
    ignore_logger("django.security.DisallowedHost")

# SMS API KEYS
SNS_ACCESS_KEY = env("SNS_ACCESS_KEY", default="")
SNS_SECRET_KEY = env("SNS_SECRET_KEY", default="")
SNS_REGION = env("SNS_REGION", default="ap-south-1")
SNS_ROLE_BASED_MODE = env.bool("SNS_ROLE_BASED_MODE", default=False)

# open id connect
JWKS = JsonWebKey.import_key_set(
    json.loads(
        base64.b64decode(env("JWKS_BASE64", default=get_jwks_from_file(BASE_DIR)))  # noqa F405
    )
)
