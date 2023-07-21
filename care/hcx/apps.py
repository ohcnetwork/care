from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HcxConfig(AppConfig):
    name = "care.hcx"
    verbose_name = _("HCX Integration")
