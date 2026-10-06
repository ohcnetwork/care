from django.apps import AppConfig

PLUGIN_NAME = "care_mcp"


class CareMcpConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = "Care MCP Server"
    default_auto_field = "django.db.models.BigAutoField"
