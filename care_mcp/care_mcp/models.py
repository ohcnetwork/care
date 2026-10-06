import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from care.utils.models.base import BaseModel

TOKEN_PREFIX = "care_mcp_"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


class MCPAccessToken(BaseModel):
    """A personal access token that lets an MCP client act as a Care user.

    Only the SHA-256 hash of the token is stored. The plaintext is returned once,
    when the token is created.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_access_tokens",
    )
    name = models.CharField(max_length=255)
    token_hash = models.CharField(max_length=64, unique=True)
    # First characters of the token, so a user can tell their tokens apart.
    token_prefix = models.CharField(max_length=24)
    allow_writes = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.name} ({self.token_prefix}…)"

    @classmethod
    def issue(cls, user, name, expires_in_days=None, allow_writes=False):
        """Create a token and return ``(instance, plaintext)``."""
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
        expires_at = (
            timezone.now() + timedelta(days=expires_in_days)
            if expires_in_days
            else None
        )
        token = cls.objects.create(
            user=user,
            name=name,
            token_hash=hash_token(raw),
            token_prefix=raw[: len(TOKEN_PREFIX) + 6],
            allow_writes=allow_writes,
            expires_at=expires_at,
        )
        return token, raw

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_active(self):
        return not self.deleted and self.revoked_at is None and not self.is_expired

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "modified_date"])
