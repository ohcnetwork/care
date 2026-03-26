from django.db import models
from care.users.models import User
from care.utils.models.base import BaseModel


class WhatsAppProfile(BaseModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="whatsapp_profile"
    )
    whatsapp_id = models.CharField(max_length=255, unique=True)
    is_verified = models.BooleanField(default=False)
    can_receive_ppi = models.BooleanField(
        default=False, help_text="Can this user receive Private Personal Information?"
    )

    def __str__(self):
        return f"{self.user.username} ({self.whatsapp_id})"
