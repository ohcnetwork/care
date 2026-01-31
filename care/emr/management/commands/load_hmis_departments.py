import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.management.commands.load_emr_utils import (
    read_csv_from_file,
    read_csv_from_google_sheet,
    read_csv_from_url,
)
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
        return {
            "department_name": row["Department"],
            "sub_department_name": row["Sub Department"],
        }

    def handle(self, *args, **options):
        with transaction.atomic():
            facility_id = options.get("facility")
            rows = self.load_data(options)

            facility = Facility.objects.get(external_id=facility_id)

            for row in rows:
                data = self.process_row(row)
                department, created = FacilityOrganization.objects.update_or_create(
                    facility=facility,
                    name=data["department_name"],
                    defaults={
                        "org_type": "dept",
                        "created_by": facility.created_by,
                    },
                )
                if created:
                    logger.info(f"Created department: {data['department_name']}")
                if data["sub_department_name"]:
                    sub_department, sub_created = (
                        FacilityOrganization.objects.update_or_create(
                            facility=facility,
                            name=data["sub_department_name"],
                            defaults={
                                "org_type": "dept",
                                "created_by": facility.created_by,
                                "parent": department,
                            },
                        )
                    )
                    if sub_created:
                        logger.info(
                            f"Created sub-department: {data['sub_department_name']} under {data['department_name']}"
                        )
