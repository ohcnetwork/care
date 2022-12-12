from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AbdmConfig(AppConfig):
    name = "abdm"
    verbose_name = _("ABDM Integration")

    def ready(self):
        try:
            import care.abdm.signals  # noqa F401
        except ImportError:
            pass
