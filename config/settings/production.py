from .deployment import *  # noqa

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = (  # noqa F405
    "config.authentication.CustomJWTAuthentication",
)

IS_PRODUCTION = True
USE_SMS = True
SEND_SMS_NOTIFICATION = True
