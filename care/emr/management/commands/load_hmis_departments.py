import logging
from datetime import UTC, datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.management.commands.load_emr_utils import load_data, set_logger_level
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
            default="Department & Sub Department",
            help="Sheet name (default: Department & Sub Department)",
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
        return {
            "department_name": row["Department"].strip(),
            "sub_department_name": row["Sub Department"].strip(),
        }

    def handle(self, *args, **options):
        start_time = datetime.now(tz=UTC)
        set_logger_level(logger, options.get("verbosity", 1))
        with transaction.atomic():
            facility = Facility.objects.get(external_id=options.get("facility"))
            logger.info("Loading departments for facility: %s", facility.name)

            rows = load_data(options)
            logger.info("Loaded %d rows from source", len(rows))

            if not rows:
                logger.warning("No data found to process.")
                return

            created = 0
            updated = 0

            for row in rows:
                data = self.process_row(row)
                department, created = FacilityOrganization.objects.update_or_create(
                    facility=facility,
                    name=data["department_name"],
                    defaults={
                        "org_type": "dept",
                        "created_by": facility.created_by,
                        "updated_by": facility.created_by,
                    },
                )
                if created:
                    logger.debug("Created department: %s", data["department_name"])
                    created += 1
                else:
                    logger.debug(
                        "Department already exists: %s", data["department_name"]
                    )
                    updated += 1
                if sub_department_name := data["sub_department_name"]:
                    _, sub_created = FacilityOrganization.objects.update_or_create(
                        facility=facility,
                        name=sub_department_name,
                        defaults={
                            "org_type": "dept",
                            "created_by": facility.created_by,
                            "updated_by": facility.created_by,
                            "parent": department,
                        },
                    )
                    if sub_created:
                        logger.debug(
                            "Created sub-department: %s under %s",
                            data["sub_department_name"],
                            data["department_name"],
                        )
                        created += 1
                    else:
                        logger.debug(
                            "Sub-department already exists: %s under %s",
                            data["sub_department_name"],
                            data["department_name"],
                        )
                        updated += 1
        self.stdout.write("\n=== Summary ===")
        self.stdout.write(self.style.SUCCESS("HMIS departments loaded successfully"))
        self.stdout.write(f"Total rows: {len(rows)}")
        self.stdout.write(f"Departments created: {created}")
        self.stdout.write(f"Departments updated: {updated}")
        self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
