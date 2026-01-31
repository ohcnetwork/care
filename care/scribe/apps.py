from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ScribeConfig(AppConfig):
    name = "care.scribe"
    verbose_name = _("Medical Scribe")

    def ready(self):
        pass
