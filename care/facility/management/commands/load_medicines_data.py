import json

from django.core.management import BaseCommand

from care.facility.models import MedibaseMedicine


class Command(BaseCommand):
    """
    Command to load medibase medicines
    Usage: python manage.py load_medicines_data
    """

    help = "Loads Medibase Medicines into the database from medibase.json"

    def fetch_data(self):
        with open("data/medibase.json", "r") as json_file:
            return json.load(json_file)

    def handle(self, *args, **options):
        print("Loading Medibase Medicines into the database from medibase.json")

        medibase_objects = self.fetch_data()

        if not MedibaseMedicine.objects.exists():
            MedibaseMedicine.objects.bulk_create(
                [
                    MedibaseMedicine(
                        id=medicine["id"],
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
                batch_size=5000,
                update_conflicts=True,
                unique_fields=["name"],
                update_fields=[
                    "created_date",
                    "modified_date",
                    "name",
                    "type",
                    "generic",
                    "company",
                    "contents",
                    "cims_class",
                    "atc_classification",
                ],
            )
            print("Medicines loaded successfully.")
        else:
            print("Medicines already exist in the database. Skipping bulk creation.")
