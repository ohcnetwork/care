from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LifeConfig(AppConfig):
    name = "life"
    verbose_name = _("Life Tools")

    def ready(self):
        try:
            import care.life.tasks.job_executor
            import care.life.signals  # noqa F401
        except ImportError:
            pass
