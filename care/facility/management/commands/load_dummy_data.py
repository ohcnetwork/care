import os

from django.core import management
from django.core.management import BaseCommand, CommandError


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
            raise CommandError(
                "This command is not intended to be run in production environment."
            )

        try:
            management.call_command("load_data", "kerala")
            management.call_command("seed_data")
            management.call_command("loaddata", self.BASE_URL + "users.json")
            management.call_command("loaddata", self.BASE_URL + "facility.json")
        except Exception as e:
            raise CommandError(e)
