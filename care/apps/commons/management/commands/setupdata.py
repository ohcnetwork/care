import os
import csv
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.commons import utils as commons_utils

class Command(BaseCommand):
    """
    Command to set-up the data in dB for use.
    """

    def handle(self, *args, **options):
        fixtures = [
            ("apps/accounts/fixtures/user_type.csv", "accounts.UserType"),
            ("apps/accounts/fixtures/state_fixture.csv", "accounts.State"),
            ("apps/accounts/fixtures/districts_fixture.csv", "accounts.District"),
            (
                "apps/facility/fixtures/inventory_item_fixture.csv",
                "facility.InventoryItem",
            ),
            ("apps/facility/fixtures/testing_lab_fixture.csv", "facility.TestingLab"),
            ("apps/facility/fixtures/bed_type.csv", "facility.RoomType"),
            ("apps/facility/fixtures/room_type.csv", "facility.BedType"),
            ("apps/facility/fixtures/facility_type.csv", "facility.FacilityType"),
            ("apps/facility/fixtures/ownership_type.csv", "commons.OwnershipType"),
            ("apps/facility/fixtures/facility_fixture.csv", "facility.Facility"),
            (
                "apps/patients/fixtures/patient_status_fixture.csv",
                "patients.PatientStatus",
            ),
            ("apps/patients/fixtures/patient_group.csv", "patients.PatientGroup"),
            (
                "apps/patients/fixtures/clinical_status_fixture.csv",
                "patients.ClinicalStatus",
            ),
            ("apps/patients/fixtures/covid_status_fixture.csv", "patients.CovidStatus"),
        ]

        json_fixtures_path, json_fixtures_name = commons_utils.get_json_fixtures(fixtures)
        for json_fixture in json_fixtures_name:
            self.stdout.write(f"Installing fixture {json_fixture}")
            call_command("loaddata", json_fixture)

        for file_path in json_fixtures_path:
            os.remove(file_path)
