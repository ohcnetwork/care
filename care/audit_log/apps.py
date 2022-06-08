from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuditLogConfig(AppConfig):
    name = "care.audit_log"
    verbose_name = _("Audit Log Management")

    def ready(self):
        try:
            import care.audit_log.receivers  # noqa F401
        except ImportError:
            pass
