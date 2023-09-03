import json

from django.core.management import BaseCommand

from care.facility.models import MedibaseMedicine


class Command(BaseCommand):
    """
    Command to load medibase medicines
    Usage: python manage.py load_medicines_data
    """

    help = "Loads Medibase Medicines into the database from medibase.json"  # noqa: A003

    def fetch_data(self):
        with open("data/medibase.json") as json_file:
            return json.load(json_file)

    def handle(self, *args, **options):
        self.stdout.write("Loading Medibase Medicines into the database")

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

        self.stdout.write(self.style.SUCCESS("Successfully Loaded"))
