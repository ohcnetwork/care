
import os
import csv
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    """
    Command to set-up the data in dB for use.
    """

    def handle(self, *args, **options):
        fixtures = [
            ('apps/accounts/fixtures/user_type.csv', 'accounts.UserType'),
            ('apps/accounts/fixtures/state_fixture.csv', 'accounts.State'),
            ('apps/accounts/fixtures/districts_fixture.csv', 'accounts.District'),
            ('apps/facility/fixtures/inventory_item_fixture.csv', 'facility.InventoryItem'),
            ('apps/facility/fixtures/testing_lab_fixture.csv', 'facility.TestingLab'),
            ('apps/facility/fixtures/facility_type.csv', 'facility.FacilityType'),
            ('apps/facility/fixtures/ownership_type.csv', 'commons.OwnershipType'),
            ('apps/facility/fixtures/facility_fixture.csv', 'facility.Facility'),
            ('apps/patients/fixtures/patient_status_fixture.csv', 'patients.PatientStatus'),
            ('apps/patients/fixtures/clinical_status_fixture.csv', 'patients.ClinicalStatus'),
            ('apps/patients/fixtures/covid_status_fixture.csv', 'patients.CovidStatus'),
        ]

        json_fixtures_path, json_fixtures_name = self.get_json_fixtures(fixtures)
        for json_fixture in json_fixtures_name:
            self.stdout.write(f'Installing fixture {json_fixture}')
            call_command('loaddata', json_fixture)

        for file_path in json_fixtures_path:
            os.remove(file_path)

    def get_json_fixtures(self, fixtures):
        json_fixtures = []
        json_fixtures_name = []

        for fixture in fixtures:
            data = []
            csv_file_name = fixture[0]
            model = fixture[1]
            csv_file_absolute_path = self.get_absolute_path(csv_file_name)
            json_file_absolute_path = self.get_absolute_path(csv_file_name.split('.')[0]+'.json')

            self.stdout.write(f'Creating JSON Fixture for {csv_file_name}')

            with open(csv_file_absolute_path) as csvFile:
                csvReader = csv.DictReader(csvFile)
                for rows in csvReader:
                    data.append({
                        "pk": rows['id'],
                        "model": model,
                        "fields": rows
                    })

            with open(json_file_absolute_path, 'w') as json_file:
                json_file.write(json.dumps(data, indent=4))

            self.stdout.write(f'Created JSON Fixture for {csv_file_name}')

            fixture_name = csv_file_name.split("/")[-1].split(".")[0]
            json_fixtures_name.append(fixture_name)
            json_fixtures.append(json_file_absolute_path)

        return json_fixtures, json_fixtures_name

    def get_absolute_path(self, file_name):
        return settings.BASE_DIR+"/"+file_name