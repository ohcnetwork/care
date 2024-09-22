from .base import *  # noqa

# https://github.com/adamchainz/django-cors-headers#cors_allow_all_origins-bool
CORS_ORIGIN_ALLOW_ALL = True

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa F405

# django-silk
# ------------------------------------------------------------------------------
# https://github.com/jazzband/django-silk#requirements
INSTALLED_APPS += ["silk"]  # F405
MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]  # noqa F405
SILKY_PYTHON_PROFILER = True

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # F405


# Celery
# ------------------------------------------------------------------------------

# https://docs.celeryq.dev/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

RUNSERVER_PLUS_PRINT_SQL_TRUNCATE = 100000

DISABLE_RATELIMIT = True
