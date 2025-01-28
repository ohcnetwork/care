from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EMRConfig(AppConfig):
    name = "care.emr"
    verbose_name = _("Electronic Medical Record")

    def ready(self):
        pass
