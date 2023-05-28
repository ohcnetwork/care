from .deployment import *  # noqa

# Your stuff...
# ------------------------------------------------------------------------------

MIDDLEWARE = ["config.add_slash_middleware.AddSlashMiddleware"] + MIDDLEWARE

IS_PRODUCTION = True
USE_SMS = True
SEND_SMS_NOTIFICATION = True
