import json
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction

from care.facility.models.patient_investigation import (
    PatientInvestigation,
    PatientInvestigationGroup,
)

with Path("data/investigations.json").open() as investigations_data:
    investigations = json.load(investigations_data)

with Path("data/investigation_groups.json").open() as investigation_groups_data:
    investigation_groups = json.load(investigation_groups_data)


class Command(BaseCommand):
    help = "Seed Data for Investigations"

    def handle(self, *args, **kwargs):
        investigation_group_dict = {}

        for investigation_group in investigation_groups:
            current_obj = PatientInvestigationGroup.objects.filter(
                name=investigation_group["name"]
            ).first()
            if not current_obj:
                current_obj = PatientInvestigationGroup(
                    name=investigation_group["name"]
                )
                current_obj.save()
            investigation_group_dict[str(investigation_group["id"])] = current_obj

        bulk_create_data = []
        bulk_update_data = []
        investigations_to_update_groups = []

        for investigation in investigations:
            data = {
                "name": investigation["name"],
                "unit": investigation.get("unit", ""),
                "ideal_value": investigation.get("ideal_value", ""),
                "min_value": None,
                "max_value": None,
                "investigation_type": investigation.get("type", None),
                "choices": investigation.get("choices", ""),
            }

            try:
                data["min_value"] = (
                    float(investigation["min"])
                    if investigation.get("min") is not None
                    else None
                )
            except (ValueError, TypeError):
                data["min_value"] = None

            try:
                data["max_value"] = (
                    float(investigation["max"])
                    if investigation.get("max") is not None
                    else None
                )
            except (ValueError, TypeError):
                data["max_value"] = None

            existing_obj = PatientInvestigation.objects.filter(
                name=data["name"]
            ).first()
            if existing_obj:
                for field, value in data.items():
                    setattr(existing_obj, field, value)
                bulk_update_data.append(existing_obj)
                investigations_to_update_groups.append(
                    (existing_obj, investigation["category_id"])
                )
            else:
                new_obj = PatientInvestigation(**data)
                bulk_create_data.append(new_obj)
                investigations_to_update_groups.append(
                    (new_obj, investigation["category_id"])
                )

        with transaction.atomic():
            if bulk_create_data:
                PatientInvestigation.objects.bulk_create(bulk_create_data)

            if bulk_update_data:
                PatientInvestigation.objects.bulk_update(
                    bulk_update_data,
                    fields=[
                        "unit",
                        "ideal_value",
                        "min_value",
                        "max_value",
                        "investigation_type",
                        "choices",
                    ],
                )

            for investigation_obj, category_ids in investigations_to_update_groups:
                groups_to_add = [
                    investigation_group_dict.get(str(category_id))
                    for category_id in category_ids
                ]
                investigation_obj.save()
                investigation_obj.groups.set(groups_to_add)

        self.stdout.write(
            self.style.SUCCESS("Successfully populated investigation data")
        )
