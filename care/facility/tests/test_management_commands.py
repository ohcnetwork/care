import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from care.facility.models import PatientInvestigation, PatientInvestigationGroup


class LoadPrescriptionCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("populate_investigations", verbosity=0)

        with Path("data/investigations.json").open() as investigations_data:
            cls.investigations = json.load(investigations_data)

        with Path("data/investigation_groups.json").open() as investigation_groups_data:
            cls.investigation_groups = json.load(investigation_groups_data)

    def test_number_of_entries(self):
        self.assertEqual(len(self.investigations), PatientInvestigation.objects.count())
        self.assertEqual(
            len(self.investigation_groups), PatientInvestigationGroup.objects.count()
        )

    def test_relation_between_investigations_and_groups(self):
        # taking first and last 5 data to test it out
        test_investigation_data = self.investigations[:5] + self.investigations[-5:]

        # creating a dictionary to avoid looping of group data for each check
        group_dict = {
            int(group["id"]): group["name"] for group in self.investigation_groups
        }

        for investigation_data in test_investigation_data:
            investigation = PatientInvestigation.objects.get(
                name=investigation_data["name"]
            )

            group_values = list(investigation.groups.values_list("name", flat=True))

            expected_groups = [
                group_dict[category_id]
                for category_id in investigation_data["category_id"]
            ]

            self.assertCountEqual(group_values, expected_groups)
