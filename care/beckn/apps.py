from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BecknConfig(AppConfig):
    name = "care.beckn"
    verbose_name = _("Beckn NFH Integration")

    def ready(self):
        import care.beckn.signals  # noqa: F401
