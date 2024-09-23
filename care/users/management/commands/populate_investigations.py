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
    """
    Populates Investigation seed data
    """

    help = "Seed Data for Investigations"

    def handle(self, *args, **kwargs):
        investigation_group_dict = {}

        investigation_groups_to_create = [
            PatientInvestigationGroup(name=group.get("name"))
            for group in investigation_groups
            if group.get("id") not in investigation_group_dict
        ]
        created_groups = PatientInvestigationGroup.objects.bulk_create(
            investigation_groups_to_create
        )
        investigation_group_dict.update({group.id: group for group in created_groups})

        existing_objs = PatientInvestigation.objects.filter(
            name__in=[investigation["name"] for investigation in investigations]
        )

        bulk_create_data = []
        bulk_update_data = []

        for investigation in investigations:
            data = {
                "name": investigation["name"],
                "unit": investigation.get("unit", ""),
                "ideal_value": investigation.get("ideal_value", ""),
                "min_value": (
                    None
                    if investigation.get("min_value") is None
                    else float(investigation.get("min_value"))
                ),
                "max_value": (
                    None
                    if investigation.get("max_value") is None
                    else float(investigation.get("max_value"))
                ),
                "investigation_type": investigation["type"],
                "choices": investigation.get("choices", ""),
            }

            existing_obj = existing_objs.filter(name=data["name"]).first()
            if existing_obj:
                bulk_update_data.append(existing_obj)
            else:
                new_obj = PatientInvestigation(**data)
                bulk_create_data.append(new_obj)

            group_ids = investigation.get("category_ids", [])
            groups_to_add = [
                investigation_group_dict[category_id] for category_id in group_ids
            ]
            if existing_obj:
                existing_obj.groups.set(groups_to_add)
            else:
                data["groups"] = groups_to_add

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
