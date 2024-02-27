import json

from django.core.management import BaseCommand

from care.facility.models.patient_investigation import (
    PatientInvestigation,
    PatientInvestigationGroup,
)

with open("data/investigations.json", "r") as investigations_data:
    investigations = json.load(investigations_data)

with open("data/investigation_groups.json") as investigation_groups_data:
    investigation_groups = json.load(investigation_groups_data)


class Command(BaseCommand):
    """
    Populates Investigation seed data
    """

    help = "Seed Data for Investigations"

    def handle(self, *args, **options):
        investigation_group_dict = {}

        # Assuming investigations is a list of dictionaries where each dictionary represents an investigation
        for investigation_group in investigation_groups:
            current_obj = PatientInvestigationGroup.objects.filter(
                name=investigation_group.get("name")
            ).first()
            if not current_obj:
                current_obj = PatientInvestigationGroup(
                    name=investigation_group.get("name")
                )
                current_obj.save()
            investigation_group_dict[investigation_group.get("id")] = current_obj

        for investigation in investigations:
            data = {
                "name": investigation["name"],
                "unit": investigation.get("unit", ""),
                "ideal_value": investigation.get("ideal_value", ""),
                "min_value": None
                if investigation.get("min_value") is None
                else float(investigation.get("min_value")),
                "max_value": None
                if investigation.get("max_value") is None
                else float(investigation.get("max_value")),
                "investigation_type": investigation["type"],
                "choices": investigation.get("choices", ""),
            }

            current_obj = PatientInvestigation.objects.filter(**data).first()
            if not current_obj:
                current_obj = PatientInvestigation(**data)
                current_obj.save()

            for category_id in investigation.get("category_ids", []):
                current_obj.groups.add(investigation_group_dict[category_id])

            current_obj.save()
