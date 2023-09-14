from .deployment import *  # noqa

# Your stuff...
# ------------------------------------------------------------------------------

MIDDLEWARE = [
    "config.add_slash_middleware.AddSlashMiddleware"
] + MIDDLEWARE  # noqa F405

IS_PRODUCTION = True
USE_SMS = True
SEND_SMS_NOTIFICATION = True
