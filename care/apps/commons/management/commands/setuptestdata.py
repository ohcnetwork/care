import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.commons import utils as commons_utils


class Command(BaseCommand):
    """
    Command to set-up the data in dB for use.
    """

    def handle(self, *args, **options):
        fixtures = [
            ("apps/patients/fixtures/patients_fixture_test.csv", "patients.Patient"),
            ("apps/patients/fixtures/patients_facilities_test.csv", "patients.PatientFacility",),
        ]

        """
        handling unique togetherness of PatientFacility
        """
        apps.get_model("patients.PatientFacility").objects.hard_delete()

        json_fixtures_path, json_fixtures_name = commons_utils.get_json_fixtures(fixtures)
        for json_fixture in json_fixtures_name:
            self.stdout.write(f"Installing fixture {json_fixture}")
            call_command("loaddata", json_fixture)

        for file_path in json_fixtures_path:
            os.remove(file_path)
