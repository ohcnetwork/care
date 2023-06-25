from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FacilityConfig(AppConfig):
    name = "care.facility"
    verbose_name = _("Facility Management")

    def ready(self):
        try:
            import care.facility.signals  # noqa F401
        except ImportError:
            pass
