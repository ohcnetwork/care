import imp
import logging

logger = logging.getLogger(__name__)


def get_default_django_settings_module():
    try:
        file_ = imp.find_module('local', ['care/settings'])[0]
    except ImportError:
        default_django_settings_module = "care.settings.dev"
    else:
        default_django_settings_module = "care.settings.local"
        file_.close()
    return default_django_settings_module
