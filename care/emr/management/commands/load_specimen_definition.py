"""
Management command to load Specimen Definitions from CSV/Google Sheets.

Usage:
    python manage.py load_specimen_definition <csv_file_or_url> --facility <facility_id>
    python manage.py load_specimen_definition --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from care.emr.management.commands.load_emr_utils import (
    create_slug,
    normalize_title,
    parse_code,
    read_csv_from_file,
    read_csv_from_google_sheet,
    read_csv_from_url,
    write_output_csv,
)
from care.emr.models.specimen_definition import SpecimenDefinition
from care.facility.models import Facility

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent
default_output_path = root_dir / "outputs" / "specimen_definition_output.csv"


class Command(BaseCommand):
    """
    Load Specimen Definitions from CSV or Google Sheets.

    Expected CSV columns:
    - title
    - description (optional)
    - status (optional, default: active)
    - type_collected_code
    - type_collected_system
    - type_collected_display
    - container_cap_code (optional)
    - container_cap_system (optional)
    - container_cap_display (optional)
    - container_minimumvolume (optional)
    - container_minimumvolume_unit_code (optional)
    - container_minimumvolume_unit_system (optional)
    - container_minimumvolume_unit_display (optional)
    - retention_time_value (optional)
    - retention_time_unit_code (optional)
    - retention_time_unit_system (optional)
    - retention_time_unit_display (optional)
    - preference (optional, default: preferred)
    - requirement (optional)
    - single_use (optional, default: true)
    """

    help = "Load Specimen Definitions from CSV or Google Sheets"

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            nargs="?",
            help="CSV file path or URL",
        )
        parser.add_argument(
            "--google-sheet",
            type=str,
            help="Google Sheet ID",
        )
        parser.add_argument(
            "--sheet-name",
            type=str,
            default="Sheet1",
            help="Sheet name (default: Sheet1)",
        )
        parser.add_argument(
            "--facility",
            type=str,
            required=True,
            help="Facility external ID",
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
                options["google_sheet"], options["sheet_name"]
            )
        if options["source"]:
            if options["source"].startswith("http"):
                return read_csv_from_url(options["source"])
            return read_csv_from_file(options["source"])
        raise ValueError("Must provide either source file/URL or --google-sheet")

    def process_row(self, row: dict, facility: Facility) -> dict:
        """
        Process a single CSV row into a SpecimenDefinition data dict.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            if not row.get("title"):
                raise ValueError("Missing required field: title")

            type_collected = parse_code(
                row.get("type_collected_code"),
                row.get("type_collected_system"),
                row.get("type_collected_display"),
            )
            if not type_collected:
                raise ValueError("Missing required type_collected fields")

            container_cap = parse_code(
                row.get("container_cap_code"),
                row.get("container_cap_system"),
                row.get("container_cap_display"),
            )

            minimum_volume_unit = parse_code(
                row.get("container_minimumvolume_unit_code"),
                row.get("container_minimumvolume_unit_system"),
                row.get("container_minimumvolume_unit_display"),
            )

            retention_time_unit = parse_code(
                row.get("retention_time_unit_code"),
                row.get("retention_time_unit_system"),
                row.get("retention_time_unit_display"),
            )

            container = {}
            if container_cap:
                container["cap"] = container_cap

            minimum_volume = row.get("container_minimumvolume")
            if minimum_volume and minimum_volume_unit:
                try:
                    volume_value = float(minimum_volume)
                    if volume_value > 0:
                        container["minimum_volume"] = {
                            "quantity": {
                                "value": volume_value,
                                "unit": minimum_volume_unit,
                            }
                        }
                except (ValueError, TypeError):
                    pass

            retention_time = None
            if row.get("retention_time_value") and retention_time_unit:
                try:
                    retention_time = {
                        "value": float(row["retention_time_value"]),
                        "unit": retention_time_unit,
                    }
                except (ValueError, TypeError):
                    pass

            # Set default retention time if not provided
            if not retention_time:
                retention_time = {
                    "value": 24,
                    "unit": {
                        "code": "h",
                        "display": "hours",
                        "system": "http://unitsofmeasure.org",
                    },
                }

            type_tested = {
                "is_derived": bool(row.get("is_derived", False)),
                "preference": row.get("preference", "preferred"),
                "retention_time": retention_time,
                "single_use": bool(row.get("single_use", True)),
            }

            if container:
                type_tested["container"] = container

            if row.get("requirement"):
                type_tested["requirement"] = row["requirement"]

            title = normalize_title(row["title"])
            slug_value = create_slug(title)

            return {
                "title": title,
                "slug_value": slug_value,
                "status": row.get("status", "active"),
                "description": row.get("description", ""),
                "type_collected": type_collected,
                "type_tested": type_tested,
            }

        except (KeyError, ValueError) as e:
            error_message = f"Failed to process row: {e}"
            raise ValueError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error processing row: {e}"
            raise RuntimeError(error_message) from e

    def create_specimen_definition(
        self, data: dict, facility: Facility, created_by
    ) -> SpecimenDefinition:
        """
        Create or update a SpecimenDefinition.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            full_slug = SpecimenDefinition.calculate_slug_from_facility(
                str(facility.external_id), data["slug_value"]
            )

            existing = SpecimenDefinition.objects.filter(
                title__iexact=data["title"], facility=facility
            ).first()

            if existing:
                logger.warning("Specimen definition already exists: %s", data["title"])
                return existing

            specimen = SpecimenDefinition(
                facility=facility,
                slug=full_slug,
                title=data["title"],
                status=data["status"],
                description=data["description"],
                type_collected=data["type_collected"],
                type_tested=data["type_tested"],
                created_by=created_by,
                updated_by=created_by,
            )
            specimen.save()
            logger.debug("Created specimen: %s", data["title"])
            return specimen

        except Exception as e:
            error_message = (
                f"Failed to create specimen '{data.get('title', 'Unknown')}': {e}"
            )
            raise RuntimeError(error_message) from e

    def handle(self, *args, **options):
        start_time = datetime.now(tz=UTC)

        # Set logging level
        if options["verbosity"] == 0:
            logger.setLevel(logging.ERROR)
        elif options["verbosity"] == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        try:
            facility = Facility.objects.get(external_id=options["facility"])
            logger.info("Loading specimens for facility: %s", facility.name)

            rows = self.load_data(options)
            logger.info("Loaded %d rows from source", len(rows))

            if not rows:
                self.stdout.write(self.style.WARNING("No rows found in source"))
                return

            batch_size = options["batch_size"]
            total_rows = len(rows)
            successful = []
            failed = []
            output_rows = []

            for i in range(0, total_rows, batch_size):
                batch = rows[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_rows + batch_size - 1) // batch_size

                logger.info(
                    "Processing batch %d/%d (rows %d-%d)",
                    batch_num,
                    total_batches,
                    i + 1,
                    min(i + batch_size, total_rows),
                )

                for row in batch:
                    row_title = row.get("title", "Unknown")
                    slug_value = ""

                    try:
                        data = self.process_row(row, facility)
                        slug_value = data["slug_value"]

                        self.create_specimen_definition(data, facility, None)

                        successful.append(slug_value)
                        output_rows.append(
                            {
                                "title": data["title"],
                                "slug_value": slug_value,
                                "status": "Success",
                                "error": "",
                            }
                        )

                    except Exception as e:
                        logger.error("Error processing row '%s': %s", row_title, e)
                        failed.append(row_title)
                        output_rows.append(
                            {
                                "title": row_title,
                                "slug_value": slug_value,
                                "status": "Failed",
                                "error": str(e),
                            }
                        )

            output_path = options.get("output") or default_output_path
            if output_path:
                write_output_csv(
                    output_path,
                    output_rows,
                    ["title", "slug_value", "status", "error"],
                )

            self.stdout.write("\n=== Summary ===")
            self.stdout.write(f"Total rows: {total_rows}")
            self.stdout.write(self.style.SUCCESS(f"Successful: {len(successful)}"))
            self.stdout.write(self.style.ERROR(f"Failed: {len(failed)}"))
            self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
            self.stdout.write(
                self.style.SUCCESS("Specimen definitions loaded successfully")
            )

        except Exception as e:
            logger.exception("Error in main process")
            error_message = f"Error in main process: {e}"
            self.stdout.write(self.style.ERROR(error_message))
            raise
