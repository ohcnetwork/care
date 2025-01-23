import base64
import json

from authlib.jose import JsonWebKey

from care.utils.jwks.generate_jwk import get_jwks_from_file

from .base import *  # noqa
from .base import BASE_DIR, TEMPLATES, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# TEMPLATES
# ------------------------------------------------------------------------------
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
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# Your stuff...
# ------------------------------------------------------------------------------

DATABASES = {"default": env.db("DATABASE_URL", default="postgres:///care-test")}

# test in peace
CACHES = {
    "default": {
        "BACKEND": "config.caches.DummyCache",
    }
}
# for testing retelimit use override_settings decorator
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

# https://whitenoise.evans.io/en/stable/django.html#whitenoise-makes-my-tests-run-slow
WHITENOISE_AUTOREFRESH = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s %(message)s"}
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "audit_log": {
            "handlers": ["console"],
            "level": "ERROR",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

CELERY_TASK_ALWAYS_EAGER = True


# open id connect
JWKS = JsonWebKey.import_key_set(
    json.loads(
        base64.b64decode(
            env(
                "JWKS_BASE64",
                default=get_jwks_from_file(BASE_DIR),
            )
        )
    )
)
