import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.http.response import Http404
from django.urls import reverse
from django_ratelimit.core import is_ratelimited
from rest_framework import mixins, serializers, status
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from care_mcp.authentication import MCPTokenAuthentication
from care_mcp.models import MCPAccessToken
from care_mcp.protocol import (
    INVALID_REQUEST,
    PARSE_ERROR,
    SUPPORTED_PROTOCOL_VERSIONS,
    error_response,
    handle_message,
)
from care_mcp.settings import plugin_settings
from care_mcp.tools import ToolContext
from config.authentication import CustomJWTAuthentication

MAX_ACTIVE_TOKENS_PER_USER = 20


def _allowed_origins() -> set[str]:
    raw = plugin_settings.CARE_MCP_ALLOWED_ORIGINS
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


class MCPView(APIView):
    """The MCP endpoint (Streamable HTTP transport, JSON responses).

    Accepts a Care MCP access token or a regular Care JWT as a Bearer token.
    """

    authentication_classes = [MCPTokenAuthentication, CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        if not plugin_settings.CARE_MCP_ENABLED:
            raise Http404
        # Reject browser pages on other origins before doing any work.
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") not in _allowed_origins():
            raise PermissionDenied("Origin not allowed.")
        super().initial(request, *args, **kwargs)

        version = request.headers.get("MCP-Protocol-Version")
        if version and version not in SUPPORTED_PROTOCOL_VERSIONS:
            raise ValidationError(
                {"detail": f"Unsupported MCP-Protocol-Version: {version}"}
            )
        rate = plugin_settings.CARE_MCP_RATE_LIMIT
        if (
            rate
            and not settings.DISABLE_RATELIMIT
            and is_ratelimited(
                request._request,  # noqa: SLF001
                group="care_mcp",
                key="user",
                rate=rate,
                increment=True,
            )
        ):
            raise Throttled

    def _context(self, request) -> ToolContext:
        token = request.auth if isinstance(request.auth, MCPAccessToken) else None
        allow_writes = plugin_settings.CARE_MCP_ALLOW_WRITES and (
            token is None or token.allow_writes
        )
        return ToolContext(user=request.user, allow_writes=allow_writes)

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse(
                error_response(None, PARSE_ERROR, "Parse error."), status=400
            )

        ctx = self._context(request)
        # JSON-RPC batches were dropped in protocol 2025-06-18 but older clients
        # may still send them.
        if isinstance(payload, list):
            if not payload:
                return JsonResponse(
                    error_response(None, INVALID_REQUEST, "Empty batch."), status=400
                )
            responses = [r for m in payload if (r := handle_message(ctx, m))]
            if not responses:
                return HttpResponse(status=status.HTTP_202_ACCEPTED)
            return JsonResponse(responses, safe=False)

        response = handle_message(ctx, payload)
        if response is None:
            return HttpResponse(status=status.HTTP_202_ACCEPTED)
        return JsonResponse(response)


class MCPAccessTokenSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    expires_in_days = serializers.IntegerField(
        write_only=True, required=False, min_value=1
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = MCPAccessToken
        fields = [
            "id",
            "name",
            "token_prefix",
            "allow_writes",
            "expires_in_days",
            "expires_at",
            "last_used_at",
            "revoked_at",
            "created_date",
            "is_active",
        ]
        read_only_fields = [
            "token_prefix",
            "expires_at",
            "last_used_at",
            "revoked_at",
            "created_date",
        ]

    def validate_expires_in_days(self, value):
        maximum = plugin_settings.CARE_MCP_TOKEN_MAX_EXPIRY_DAYS
        if value > maximum:
            msg = f"Tokens can last at most {maximum} days."
            raise serializers.ValidationError(msg)
        return value

    def validate_allow_writes(self, value):
        if value and not plugin_settings.CARE_MCP_ALLOW_WRITES:
            msg = "Write access is disabled on this Care server."
            raise serializers.ValidationError(msg)
        return value


class MCPAccessTokenViewSet(
    mixins.ListModelMixin, mixins.DestroyModelMixin, GenericViewSet
):
    """The caller's own MCP access tokens. Requires a normal Care login, so an
    MCP token can never be used to mint or revoke tokens."""

    serializer_class = MCPAccessTokenSerializer
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"

    def get_queryset(self):
        return MCPAccessToken.objects.filter(user=self.request.user, deleted=False)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        active = [t for t in self.get_queryset() if t.is_active]
        if len(active) >= MAX_ACTIVE_TOKENS_PER_USER:
            raise ValidationError(
                {"detail": "Too many active tokens. Revoke one first."}
            )
        token, raw = MCPAccessToken.issue(
            user=request.user,
            name=serializer.validated_data["name"],
            expires_in_days=serializer.validated_data.get(
                "expires_in_days",
                plugin_settings.CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS,
            ),
            allow_writes=serializer.validated_data.get("allow_writes", False),
        )
        data = self.get_serializer(token).data
        data["token"] = raw  # shown once, never stored
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        instance.revoke()


class ConfigView(APIView):
    """What a client (or Care's frontend) needs to connect."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "enabled": plugin_settings.CARE_MCP_ENABLED,
                "endpoint": request.build_absolute_uri(reverse("care-mcp-endpoint")),
                "allow_writes": plugin_settings.CARE_MCP_ALLOW_WRITES,
                "protocol_versions": list(SUPPORTED_PROTOCOL_VERSIONS),
                "token_default_expiry_days": (
                    plugin_settings.CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS
                ),
                "token_max_expiry_days": plugin_settings.CARE_MCP_TOKEN_MAX_EXPIRY_DAYS,
            }
        )
