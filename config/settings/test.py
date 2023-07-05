"""
With these settings, tests run faster.
"""

from care.facility.static_data.medibase import MedibaseMedicineTable  # noqa

from .base import *  # noqa
from .base import env

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
TEMPLATES[-1]["OPTIONS"]["loaders"] = [  # type: ignore[index] # noqa F405
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
DATABASES["default"]["ATOMIC_REQUESTS"] = True

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
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
}

CELERY_TASK_ALWAYS_EAGER = True
