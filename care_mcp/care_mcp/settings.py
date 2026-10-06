"""Plugin settings.

Resolution order for every key:
    settings.PLUGIN_CONFIGS["care_mcp"][key]  →  environment variable  →  DEFAULTS[key]

The environment cast is inferred from the *type of the default*, so every default must be
correctly typed (use "" / 0 / False, never None).
"""

from typing import Any

import environ
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.dispatch import receiver
from rest_framework.settings import perform_import

from care_mcp.apps import PLUGIN_NAME

env = environ.Env()


class PluginSettings:  # pragma: no cover
    """Access plugin settings as attributes.

    >>> from care_mcp.settings import plugin_settings
    >>> plugin_settings.CARE_MCP_ENABLED
    """

    def __init__(
        self,
        plugin_name: str | None = None,
        defaults: dict | None = None,
        import_strings: set | None = None,
        required_settings: set | None = None,
    ) -> None:
        if not plugin_name:
            raise ValueError("Plugin name must be provided")
        self.plugin_name = plugin_name
        self.defaults = defaults or {}
        self.import_strings = import_strings or set()
        self.required_settings = required_settings or set()
        self._cached_attrs = set()
        self.validate()

    def __getattr__(self, attr) -> Any:
        if attr not in self.defaults:
            msg = f"Invalid setting: '{attr}'"
            raise AttributeError(msg)

        val = self.defaults[attr]
        try:
            val = self.user_settings[attr]
        except KeyError:
            try:
                val = env(attr, cast=type(val))
            except environ.ImproperlyConfigured:
                # Not set in the environment either: keep the default.
                val = self.defaults[attr]

        if attr in self.import_strings:
            val = perform_import(val, attr)

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    @property
    def user_settings(self) -> dict:
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, "PLUGIN_CONFIGS", {}).get(
                self.plugin_name, {}
            )
        return self._user_settings

    def validate(self) -> None:
        if (
            self.CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS
            > self.CARE_MCP_TOKEN_MAX_EXPIRY_DAYS
        ):
            raise ImproperlyConfigured(
                "CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS cannot exceed "
                "CARE_MCP_TOKEN_MAX_EXPIRY_DAYS."
            )
        for setting in self.required_settings:
            if not getattr(self, setting):
                msg = (
                    f'The "{setting}" setting is required. '
                    f"Set it in the environment or in the {PLUGIN_NAME} plugin config."
                )
                raise ImproperlyConfigured(msg)

    def reload(self) -> None:
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


# Credentials without which the plugin cannot function. A misconfigured deploy fails at boot.
REQUIRED_SETTINGS: set[str] = set()

DEFAULTS = {
    # Master switch for the MCP endpoint.
    "CARE_MCP_ENABLED": True,
    # Expose tools that create, update or delete data. Off by default: the server is
    # read-only unless an operator opts in, and then only for tokens that also allow writes.
    "CARE_MCP_ALLOW_WRITES": False,
    # Tool results longer than this many characters are truncated before they reach
    # the model, so one large list cannot blow up the client's context window.
    "CARE_MCP_MAX_RESPONSE_CHARS": 50000,
    # Default and maximum lifetime of personal MCP access tokens, in days.
    "CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS": 30,
    "CARE_MCP_TOKEN_MAX_EXPIRY_DAYS": 90,
    # Per-user rate limit for MCP requests (django-ratelimit syntax). "" disables it.
    "CARE_MCP_RATE_LIMIT": "120/m",
    # Comma-separated browser origins allowed to call the endpoint. Requests that carry
    # an Origin header not in this list are rejected (DNS-rebinding protection, as the
    # MCP spec requires). Desktop and CLI clients do not send Origin.
    "CARE_MCP_ALLOWED_ORIGINS": "",
}

plugin_settings = PluginSettings(
    PLUGIN_NAME, defaults=DEFAULTS, required_settings=REQUIRED_SETTINGS
)


@receiver(setting_changed)
def reload_plugin_settings(*args, **kwargs) -> None:
    if kwargs["setting"] == "PLUGIN_CONFIGS":
        plugin_settings.reload()
