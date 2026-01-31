import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.management.commands.load_emr_utils import (
    read_csv_from_file,
    read_csv_from_google_sheet,
    read_csv_from_url,
)
from care.emr.models import FacilityLocation
from care.facility.models import Facility

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "script to load hmis data from google sheets"

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            nargs="?",
            help="CSV file path or URL",
        )
        parser.add_argument(
            "--facility",
            type=str,
            required=True,
            help="Facility external ID",
        )
        parser.add_argument(
            "--google-sheet",
            type=str,
            help="Google Sheet ID",
        )
        parser.add_argument(
            "--sheet-gid",
            type=str,
            default="000",
            help="Sheet gid (default: 000)",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output CSV file path",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for processing (default: 100)",
        )

    def load_data(self, options):
        """Load data from source."""
        if options["google_sheet"]:
            return read_csv_from_google_sheet(
                options["google_sheet"], options["sheet_gid"]
            )
        if options["source"]:
            if options["source"].startswith("http"):
                return read_csv_from_url(options["source"])
            return read_csv_from_file(options["source"])
        raise ValueError("Must provide either source file/URL or --google-sheet")

    def process_row(self, row: dict):
        # Building	Type	Description	Level	Type	Description	Room/Ward/Wing	Type	Description	Bed	Type	Description	Department	Sub-Department
        print(row)
        return {
            "building_name": row["Building"],
            "building_type": row["Type"],
            "building_description": row["Description"],
            "level_name": row["Level"],
            "level_type": row["Type"],
            "level_description": row["Description"],
            "room_name": row["Room/Ward/Wing"],
            "room_type": row["Type"],
            "room_description": row["Description"],
            "bed_name": row["Bed"],
            "bed_type": row["Type"],
            "bed_description": row["Description"],
            "department_name": row["Department"],
            "sub_department_name": row["Sub-Department"],
        }

    def handle(self, *args, **options):
        logger.setLevel(options["verbosity"])
        with transaction.atomic():
            facility_id = options.get("facility")

            facility = Facility.objects.get(external_id=facility_id)

            rows = self.load_data(options)

            for row in rows:
                data = self.process_row(row)
                building, building_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=None,
                    name=data["building_name"].strip(),
                    defaults={
                        "status": "active",
                        "operational_status": "O",
                        "description": data["building_description"],
                        "form": "bu",
                        "mode": "kind",
                    },
                )
                if building_created:
                    logger.info(f"Created Building: {building.name}")
                level, level_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=building,
                    name=data["level_name"].strip(),
                    defaults={
                        "operational_status": "O",
                        "description": data["level_description"],
                        "form": "lvl",
                        "mode": "kind",
                    },
                )
                if level_created:
                    logger.info(f"  Created Level: {level.name}")
                room, room_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=level,
                    name=data["room_name"].strip(),
                    defaults={
                        "operational_status": "O",
                        "description": data["room_description"],
                        "form": "ro",
                        "mode": "kind",
                    },
                )
                if room_created:
                    logger.info(f"    Created Room: {room.name}")
                if room.has_children:
                    logger.info("      Room already has beds, skipping bed creation.")
                    continue
                # create number of beds as per bed_name
                bed_count = 0  # default
                try:
                    bed_count = int(data["bed_name"].strip())
                except ValueError:
                    logger.warning(
                        f"      Invalid bed count '{data['bed_name']}' for room {room.name}, skipping bed creation."
                    )
                    continue

                for i in range(bed_count):
                    bed, bed_created = FacilityLocation.objects.update_or_create(
                        facility=facility,
                        parent=room,
                        name=f"Bed {i + 1}",
                        defaults={
                            "operational_status": "O",
                            "description": data["bed_description"],
                            "form": "bd",
                            "mode": "instance",
                        },
                    )
                    if bed_created:
                        logger.info(f"      Created Bed: {bed.name}")
