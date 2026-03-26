from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from care.utils.models.base import BaseModel


class WhatsAppProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="whatsapp_profile"
    )
    whatsapp_id = models.CharField(
        max_length=255,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\+?[1-9]\d{7,14}$",
                message="WhatsApp ID must be in E.164 format: '+[country code][number]'. Up to 15 digits.",
            )
        ],
    )
    is_verified = models.BooleanField(default=False)
    can_receive_ppi = models.BooleanField(
        default=False,
        help_text="Can this user receive Personally Identifiable Information?",
    )

    def clean(self):
        # Normalize WhatsApp ID (strip spaces and dashes)
        if self.whatsapp_id:
            self.whatsapp_id = self.whatsapp_id.strip().replace(" ", "").replace("-", "")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.whatsapp_id})"
