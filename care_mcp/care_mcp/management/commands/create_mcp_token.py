from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from care_mcp.models import MCPAccessToken
from care_mcp.settings import plugin_settings


class Command(BaseCommand):
    help = "Create a Care MCP access token for a user and print it once."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--name", default="CLI token")
        parser.add_argument(
            "--days",
            type=int,
            default=plugin_settings.CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS,
        )
        parser.add_argument("--allow-writes", action="store_true")

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist as e:
            msg = f"No user named {options['username']}"
            raise CommandError(msg) from e
        maximum = plugin_settings.CARE_MCP_TOKEN_MAX_EXPIRY_DAYS
        if not 1 <= options["days"] <= maximum:
            msg = f"--days must be between 1 and {maximum}"
            raise CommandError(msg)
        if options["allow_writes"] and not plugin_settings.CARE_MCP_ALLOW_WRITES:
            msg = "CARE_MCP_ALLOW_WRITES is off on this server."
            raise CommandError(msg)
        _, raw = MCPAccessToken.issue(
            user=user,
            name=options["name"],
            expires_in_days=options["days"],
            allow_writes=options["allow_writes"],
        )
        self.stdout.write(raw)
