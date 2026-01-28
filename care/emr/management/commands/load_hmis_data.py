import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "script to load hmis data from google sheets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--facility_id",
            type=str,
            help="Facility External ID to load HMIS data for",
        )
        parser.add_argument(
            "--sheet_url",
            type=str,
            help="Google Sheet URL to load HMIS data from",
        )
        parser.add_argument(
            "--verbosity",
            type=str,
            default="INFO",
            help="Verbosity level for the command output",
        )

    def handle(self, *args, **options):
        logger.setLevel(options["verbosity"])
        logger.info("Starting HMIS data load process...")
        with transaction.atomic():
            facility_id = options.get("facility_id")
            sheet_url = options.get("sheet_url")
            if not facility_id or not sheet_url:
                logger.error("Both facility_id and sheet_url are required.")
                return
            logger.info(
                "Loading HMIS data for facility %s from %s", facility_id, sheet_url
            )
            logger.info("Loading HMIS Departments...")
            call_command(
                "load_hmis_departments",
                facility=facility_id,
                sheet_url=sheet_url,
                verbosity=options["verbosity"],
            )
            # TODO: Add more commands hare
