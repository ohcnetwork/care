from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ParxioCoreConfig(AppConfig):
    name = "care.parxio_core"
    verbose_name = _("Parxio Core")

    def ready(self):
        import care.parxio_core.signals  # noqa: F401
