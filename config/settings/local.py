import base64
import json

from authlib.jose import JsonWebKey

from care.utils.jwks.generate_jwk import get_jwks_from_file

from .base import *  # noqa
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE, env

# https://github.com/adamchainz/django-cors-headers#cors_allow_all_origins-bool
CORS_ORIGIN_ALLOW_ALL = True

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]

# django-silk
# ------------------------------------------------------------------------------
# https://github.com/jazzband/django-silk#requirements
if env("ENABLE_SILK", default=False):
    INSTALLED_APPS += ["silk"]
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
# https://github.com/jazzband/django-silk#profiling
SILKY_PYTHON_PROFILER = True

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]


# Celery
# ------------------------------------------------------------------------------

# https://docs.celeryq.dev/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

RUNSERVER_PLUS_PRINT_SQL_TRUNCATE = None

RUNSERVERPLUS_POLLER_RELOADER_TYPE = "watchdog"


DISABLE_RATELIMIT = True

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

SMS_BACKEND = "care.utils.sms.backend.console.ConsoleBackend"
