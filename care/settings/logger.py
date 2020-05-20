# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

import os


class LoggerSettingsMixin(object):
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s [%(pathname)s] [%(funcName)s] [%(lineno)d] %(message)s'
            },
            'simple': {
                'format': '%(name)s %(levelname)s [%(pathname)s] %(funcName)s %(message)s'
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            },
        },
        'handlers': {
            'null': {
                'level': 'DEBUG',
                'class': 'logging.NullHandler',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            },
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler',
            }
        },
        'loggers': {
            'django': {
                'handlers': ['console', ],
                'propagate': True,
                'level': 'INFO',
            },
            'django.request': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console', ],
                'level': 'INFO',
                'propagate': False,
            },
            # Catch All Logger -- Captures any other logging
            '': {
                'handlers': ['console', ],
                'level': 'INFO',
                'propagate': True,
            }
        }
    }
