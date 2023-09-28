import json

from django.core.management import BaseCommand, CommandParser

from care.facility.models.meta_hub_spokes import MetaHubSpokes


class Command(BaseCommand):
    """
    Management command to load a state's hub and spoke data from JSON
    Usage: python manage.py load_meta_hub_spokes <state>
    """

    help = "Load a state's hub and spoke data from JSON"
    JSON_URL = "data/hub_spokes.json"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("state", help="")

    def handle(self, *args, **options):
        state = options["state"]

        self.stdout.write(f"Loading hub and spoke data for {state}...")

        with open(self.JSON_URL) as f:
            entries = json.load(f)

        objects = [MetaHubSpokes(**e) for e in entries if e["state"].lower() == state]

        MetaHubSpokes.objects.all().delete()
        MetaHubSpokes.objects.bulk_create(objects)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully loaded hub and spoke data for {state}")
        )
