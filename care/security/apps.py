from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SecurityConfig(AppConfig):
    name = "care.security"
    verbose_name = _("Security Management")

    def ready(self):
        # import care.security.signals  # noqa F401
        pass
