import imp
import logging

logger = logging.getLogger(__name__)


def get_default_django_settings_module():
    try:
        file_ = imp.find_module('local', ['covid19/settings'])[0]
    except ImportError:
        default_django_settings_module = "covid19.settings.dev"
    else:
        default_django_settings_module = "covid19.settings.local"
        file_.close()
    return default_django_settings_module
