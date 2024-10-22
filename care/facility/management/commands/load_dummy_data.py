import os

from django.core import management
from django.core.management import BaseCommand, CommandError
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)


class Command(BaseCommand):
    """
    Management command to load dummy data intended to be used for development
    and testing purposes only. Not for production use.
    Usage: python manage.py load_dummy_data
    """

    help = "Loads dummy data that is intended to be used for development and testing purpose."
    BASE_URL = "data/dummy/"

    def handle(self, *args, **options):
        env = os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
        if "production" in env or "staging" in env:
            msg = "This command is not intended to be run in production environment."
            raise CommandError(msg)

        # Disconnecting signals temporarily to avoid conflicts
        signals_to_disconnect = [
            post_save,
            post_delete,
            pre_save,
            pre_delete,
            m2m_changed,
        ]
        original_receivers = {}

        for signal in signals_to_disconnect:
            original_receivers[signal] = signal.receivers
            signal.receivers = []

        try:
            management.call_command("loaddata", self.BASE_URL + "states.json")
            management.call_command("load_skill_data")
            management.call_command("seed_data")
            management.call_command(
                "loaddata",
                self.BASE_URL + "users.json",
                self.BASE_URL + "facility.json",
            )
            management.call_command("populate_investigations")
        except Exception as e:
            raise CommandError(e) from e
        finally:
            # Reconnect original signals
            for signal in signals_to_disconnect:
                signal.receivers = original_receivers[signal]
