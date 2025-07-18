from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WhatsAppBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "care_whatsapp_bot"
    verbose_name = _("WhatsApp Bot for CARE")

    def ready(self):
        # Import signal handlers when the app is ready
        try:
            import care_whatsapp_bot.signals  # noqa F401
        except ImportError:
            pass