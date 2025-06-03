import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetToken(models.Model):
    """Model for storing password reset tokens"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_password_reset_tokens",  # Changed from "password_reset_tokens"
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    user_agent = models.CharField(max_length=256, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def __str__(self):
        return f"Password reset token for user {self.user}"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        if not self.expires_at:
            expiry_hours = getattr(settings, "PASSWORD_RESET_EXPIRY_HOURS", 24)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        """Generate a cryptographically strong unique token key"""
        return secrets.token_urlsafe(48)  # 64 characters in base64 encoding

    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def clear_expired(cls):
        """Delete all expired tokens"""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
