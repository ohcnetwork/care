from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from care_mcp.models import TOKEN_PREFIX, MCPAccessToken, hash_token

# Avoid a database write on every request; a minute of precision is plenty.
LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)


class MCPTokenAuthentication(BaseAuthentication):
    """Authenticates ``Authorization: Bearer care_mcp_…`` personal access tokens.

    Bearer values that are not MCP tokens are left for the next authenticator,
    so Care's own JWTs keep working on the same endpoint.
    """

    keyword = b"bearer"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if len(auth) != 2 or auth[0].lower() != self.keyword:  # noqa: PLR2004
            return None
        try:
            raw = auth[1].decode()
        except UnicodeError:
            return None
        if not raw.startswith(TOKEN_PREFIX):
            return None

        token = (
            MCPAccessToken.objects.select_related("user")
            .filter(token_hash=hash_token(raw), deleted=False)
            .first()
        )
        if token is None or not token.is_active:
            raise AuthenticationFailed("Invalid, expired or revoked MCP token.")
        if not token.user.is_active:
            raise AuthenticationFailed("User is inactive.")

        now = timezone.now()
        if (
            token.last_used_at is None
            or now - token.last_used_at > LAST_USED_UPDATE_INTERVAL
        ):
            MCPAccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
        return token.user, token

    def authenticate_header(self, request):
        return 'Bearer realm="care-mcp"'
