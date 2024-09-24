import json
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management import BaseCommand

from care.facility.models import MedibaseMedicine

if TYPE_CHECKING:
    from pathlib import Path


class Command(BaseCommand):
    """
    Command to load medibase medicines
    Usage: python manage.py load_medicines_data
    """

    help = "Loads Medibase Medicines into the database from medibase.json"

    def fetch_data(self):
        medibase_json: Path = settings.BASE_DIR / "data" / "medibase.json"
        with medibase_json.open() as json_file:
            return json.load(json_file)

    def handle(self, *args, **options):
        self.stdout.write(
            "Loading Medibase Medicines into the database from medibase.json"
        )

        medibase_objects = self.fetch_data()
        MedibaseMedicine.objects.bulk_create(
            [
                MedibaseMedicine(
                    name=medicine["name"],
                    type=medicine["type"],
                    company=medicine.get("company"),
                    contents=medicine.get("contents"),
                    cims_class=medicine.get("cims_class"),
                    atc_classification=medicine.get("atc_classification"),
                    generic=medicine.get("generic"),
                )
                for medicine in medibase_objects
            ],
            batch_size=1000,
            ignore_conflicts=True,
        )
