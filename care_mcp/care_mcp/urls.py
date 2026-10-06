"""Mounted by Care at /api/care_mcp/ (config/urls.py loops over PLUGIN_APPS)."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from care_mcp.views import ConfigView, MCPAccessTokenViewSet, MCPView

router = SimpleRouter()
router.register("tokens", MCPAccessTokenViewSet, basename="care-mcp-tokens")

urlpatterns = [
    path("mcp/", MCPView.as_view(), name="care-mcp-endpoint"),
    path("config/", ConfigView.as_view(), name="care-mcp-config"),
    *router.urls,
]
