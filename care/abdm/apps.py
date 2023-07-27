from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AbdmConfig(AppConfig):
    name = "care.abdm"
    verbose_name = _("ABDM Integration")
