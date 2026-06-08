from .deployment import *  # noqa

ALLOWED_HOSTS = ["*"]

# Your stuff...
# ------------------------------------------------------------------------------

IS_PRODUCTION = True

USE_SMS = env.bool("USE_SMS", default=True)  # noqa F405
