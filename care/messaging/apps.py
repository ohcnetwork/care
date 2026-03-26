from django.apps import AppConfig
<<<<<<< HEAD


class MessagingConfig(AppConfig):
    name = "care.messaging"
    verbose_name = "Messaging"
=======
from django.utils.translation import gettext_lazy as _

class MessagingConfig(AppConfig):
    name = "care.messaging"
    verbose_name = _("Messaging")
>>>>>>> feature/auth-flow
