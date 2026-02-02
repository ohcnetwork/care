import logging
from datetime import UTC, datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.management.commands.load_emr_utils import load_data, set_logger_level
from care.emr.models import FacilityLocation, FacilityLocationOrganization
from care.emr.models.organization import FacilityOrganization
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
            "--sheet-name",
            type=str,
            default="Location Mapping",
            help="Sheet name (default: Location Mapping)",
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

    def process_row(self, row: dict):
        # Building	Type	Description	Level	Type	Description	Room/Ward/Wing	Type	Description	Bed	Type	Description	Department	Sub-Department
        return {
            "building_name": row["Building"].strip(),
            "building_type": row["Building Type"].strip().lower(),
            "building_description": row["Building Description"].strip(),
            "level_name": row["Level"].strip(),
            "level_type": row["Level Type"].strip().lower(),
            "level_description": row["Level Description"].strip(),
            "room_name": row["Room/Ward/Wing"].strip(),
            "room_type": row["Room/Ward/Wing Type"].strip().lower(),
            "room_description": row["Room/Ward/Wing Description"].strip(),
            "bed_name": row["Bed"].strip(),
            "bed_type": row["Bed Type"].strip().lower(),
            "bed_description": row["Bed Description"].strip(),
            "department_name": row["Department"].strip(),
            "sub_department_name": row["Sub-Department"].strip(),
        }

    def handle(self, *args, **options):  # noqa: PLR0912, PLR0915
        start_time = datetime.now(tz=UTC)
        set_logger_level(logger, options.get("verbosity", 1))
        with transaction.atomic():
            facility = Facility.objects.get(external_id=options.get("facility"))
            logger.info("Loading locations for facility: %s", facility.name)

            rows = load_data(options)
            logger.info("Loaded %d rows from source", len(rows))
            if not rows:
                logger.warning("No data found to process.")
                return

            created = 0
            updated = 0

            for row in rows:
                data = self.process_row(row)
                if not (building_name := data["building_name"]):
                    logger.warning("Skipping row with empty building name: %s", row)
                    continue
                building, building_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=None,
                    name=building_name,
                    defaults={
                        "status": "active",
                        "operational_status": "O",
                        "description": data["building_description"],
                        "form": "bu",
                        "mode": "kind",
                        "created_by": facility.created_by,
                        "updated_by": facility.created_by,
                    },
                )
                if building_created:
                    logger.debug("Created Building: %s", building.name)
                    created += 1
                else:
                    logger.debug("Building already exists: %s", building.name)
                    updated += 1
                level, level_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=building,
                    name=data["level_name"],
                    defaults={
                        "status": "active",
                        "operational_status": "O",
                        "description": data["level_description"],
                        "form": "lvl",
                        "mode": "kind",
                        "created_by": facility.created_by,
                        "updated_by": facility.created_by,
                    },
                )
                if level_created:
                    logger.debug("  Created Level: %s", level.name)
                    created += 1
                else:
                    logger.debug("  Level already exists: %s", level.name)
                    updated += 1
                room, room_created = FacilityLocation.objects.update_or_create(
                    facility=facility,
                    parent=level,
                    name=data["room_name"],
                    defaults={
                        "status": "active",
                        "operational_status": "O",
                        "description": data["room_description"],
                        "form": "wa" if data["room_type"] == "ward" else "ro",
                        "mode": "kind",
                        "created_by": facility.created_by,
                        "updated_by": facility.created_by,
                    },
                )
                if room_created:
                    logger.debug("    Created Room: %s", room.name)
                    created += 1
                else:
                    logger.debug("    Room already exists: %s", room.name)
                    updated += 1

                if department_name := data["department_name"]:
                    org = FacilityOrganization.objects.filter(
                        name=department_name
                    ).first()
                    if sub_department_name := data["sub_department_name"]:
                        org = FacilityOrganization.objects.filter(
                            name=sub_department_name, parent=org
                        ).first()
                    if not org:
                        logger.warning(
                            "      Department/Sub-department '%s/%s' not found for room %s, skipping organization linking.",
                            department_name,
                            sub_department_name,
                            room.name,
                        )
                    else:
                        FacilityLocationOrganization.objects.get_or_create(
                            location=room, organization=org
                        )
                        logger.debug(
                            "      Linked Room %s to Organization %s",
                            room.name,
                            org.name,
                        )
                else:
                    logger.warning(
                        "      No department name provided for room %s, skipping organization linking.",
                        room.name,
                    )

                bed_count = 0
                try:
                    bed_count = int(data["bed_name"])
                except ValueError:
                    logger.warning(
                        "      Invalid bed count '%s' for room %s, skipping bed creation.",
                        data["bed_name"],
                        room.name,
                    )
                    continue

                for i in range(bed_count):
                    bed, bed_created = FacilityLocation.objects.update_or_create(
                        facility=facility,
                        parent=room,
                        name=f"Bed {i + 1}",
                        defaults={
                            "status": "active",
                            "operational_status": "O",
                            "description": data["bed_description"],
                            "form": "bd",
                            "mode": "instance",
                        },
                    )
                    if bed_created:
                        logger.debug("      Created Bed: %s", bed.name)
                        created += 1
                    else:
                        logger.debug("      Bed already exists: %s", bed.name)
                        updated += 1

        self.stdout.write("\n=== Summary ===")
        self.stdout.write(self.style.SUCCESS("HMIS locations loaded successfully"))
        self.stdout.write(f"Total rows: {len(rows)}")
        self.stdout.write(f"locations created: {created}")
        self.stdout.write(f"locations updated: {updated}")
        self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
