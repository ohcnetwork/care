from django.contrib import admin

from care_mcp.models import MCPAccessToken


@admin.register(MCPAccessToken)
class MCPAccessTokenAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "token_prefix",
        "allow_writes",
        "expires_at",
        "last_used_at",
        "revoked_at",
    )
    list_filter = ("allow_writes",)
    search_fields = ("name", "user__username", "token_prefix")
    exclude = ("token_hash",)
    readonly_fields = ("token_prefix", "last_used_at", "user")
