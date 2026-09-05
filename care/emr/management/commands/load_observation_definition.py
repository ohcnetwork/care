"""
Management command to load Observation Definitions from CSV/Google Sheets.

Usage:
    python manage.py load_observation_definition <csv_file_or_url> --facility <facility_id>
    python manage.py load_observation_definition --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
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
    validate_and_substitute_code,
    write_output_csv,
)
from care.emr.models.observation_definition import ObservationDefinition
from care.facility.models import Facility

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent
default_output_path = root_dir / "outputs" / "observation_definition_output.csv"


class Command(BaseCommand):
    """
    Load Observation Definitions from CSV or Google Sheets.

    Expected CSV columns:
    - title
    - description
    - status (optional, default: active)
    - category (optional, default: laboratory)
    - code_system
    - code_value
    - code_display
    - permitted_data_type
    - body_site_system (optional)
    - body_site_code (optional)
    - body_site_display (optional)
    - method_system (optional)
    - method_code (optional)
    - method_display (optional)
    - permitted_unit_system (optional)
    - permitted_unit_code (optional)
    - permitted_unit_display (optional)
    - derived_from_uri (optional)
    - component (optional, JSON string)
    - qualified_ranges (optional, JSON string)
    """

    help = "Load Observation Definitions from CSV or Google Sheets"

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
            help="Facility external ID (optional for system-level definitions)",
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
        parser.add_argument(
            "--validate-codes",
            action="store_true",
            default=True,
            help="Validate codes against valuesets (default: True)",
        )
        parser.add_argument(
            "--no-validate-codes",
            action="store_false",
            dest="validate_codes",
            help="Skip code validation",
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

    def process_row(
        self, row: dict, facility: Facility | None, validate_codes: bool
    ) -> dict:
        """
        Process a single CSV row into an ObservationDefinition data dict.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            import json

            if not row.get("title"):
                raise ValueError("Missing required field: title")

            code_value = row.get("code_value")
            code_system = row.get("code_system", "http://loinc.org")
            code_display = row.get("code_display")

            # Default code for observation
            default_code = {
                "code": "104922-0",
                "system": "http://loinc.org",
                "display": "Laboratory test details panel",
            }

            substitution_messages = []

            # Validate code if requested
            if validate_codes and code_value:
                code, sub_msg = validate_and_substitute_code(
                    code_value,
                    code_system,
                    "system-observation",
                    default_code,
                )
                if sub_msg:
                    substitution_messages.append(f"code: {sub_msg}")
            else:
                code = parse_code(code_value, code_system, code_display) or default_code

            body_site = parse_code(
                row.get("body_site_code"),
                row.get("body_site_system", "http://snomed.info/sct"),
                row.get("body_site_display"),
            )

            # Parse optional method
            method_code = row.get("method_code")
            method_system = row.get(
                "method_system",
                "http://terminology.hl7.org/CodeSystem/observation-methods",
            )
            method_display = row.get("method_display")

            default_method = {
                "code": "386053000",
                "system": "http://snomed.info/sct",
                "display": "Technique",
            }

            if validate_codes and method_code:
                method, sub_msg = validate_and_substitute_code(
                    method_code,
                    method_system,
                    "system-collection-method",
                    default_method,
                )
                if sub_msg:
                    substitution_messages.append(f"method: {sub_msg}")
            else:
                method = (
                    parse_code(method_code, method_system, method_display)
                    if method_code
                    else None
                )

            permitted_unit = parse_code(
                row.get("permitted_unit_code"),
                row.get("permitted_unit_system", "http://unitsofmeasure.org"),
                row.get("permitted_unit_display"),
            )

            component = []
            if row.get("component"):
                try:
                    component = json.loads(row["component"])
                    if not isinstance(component, list):
                        component = []
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Invalid component JSON for %s", row.get("title"))

            qualified_ranges = []
            if row.get("qualified_ranges"):
                try:
                    qualified_ranges = json.loads(row["qualified_ranges"])
                    if not isinstance(qualified_ranges, list):
                        qualified_ranges = []
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Invalid qualified_ranges JSON for %s", row.get("title")
                    )

            title = normalize_title(row["title"])
            slug_value = create_slug(title)

            return {
                "title": title,
                "slug_value": slug_value,
                "status": row.get("status", "active"),
                "description": row.get("description", ""),
                "category": row.get("category", "laboratory"),
                "code": code,
                "permitted_data_type": row.get("permitted_data_type", "string"),
                "body_site": body_site,
                "method": method,
                "permitted_unit": permitted_unit,
                "derived_from_uri": row.get("derived_from_uri", ""),
                "component": component,
                "qualified_ranges": qualified_ranges,
                "substitutions": "; ".join(substitution_messages)
                if substitution_messages
                else "",
            }

        except (KeyError, ValueError) as e:
            error_message = f"Failed to process row: {e}"
            raise ValueError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error processing row: {e}"
            raise RuntimeError(error_message) from e

    def create_observation_definition(
        self, data: dict, facility: Facility | None, created_by
    ) -> ObservationDefinition:
        """
        Create or update an ObservationDefinition.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            if facility:
                full_slug = ObservationDefinition.calculate_slug_from_facility(
                    str(facility.external_id), data["slug_value"]
                )
            else:
                full_slug = ObservationDefinition.calculate_slug_from_instance(
                    data["slug_value"]
                )

            existing = ObservationDefinition.objects.filter(
                title__iexact=data["title"], facility=facility
            ).first()

            if existing:
                logger.warning(
                    "Observation definition already exists: %s", data["title"]
                )
                return existing

            observation = ObservationDefinition(
                facility=facility,
                slug=full_slug,
                title=data["title"],
                status=data["status"],
                description=data["description"],
                category=data["category"],
                code=data["code"],
                permitted_data_type=data["permitted_data_type"],
                body_site=data["body_site"],
                method=data["method"],
                permitted_unit=data["permitted_unit"],
                derived_from_uri=data["derived_from_uri"],
                component=data["component"],
                qualified_ranges=data["qualified_ranges"],
                created_by=created_by,
                updated_by=created_by,
            )
            observation.save()
            logger.debug("Created observation: %s", data["title"])
            return observation

        except Exception as e:
            error_message = (
                f"Failed to create observation '{data.get('title', 'Unknown')}': {e}"
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
            facility = None
            if options.get("facility"):
                facility = Facility.objects.get(external_id=options["facility"])
                logger.info("Loading observations for facility: %s", facility.name)
            else:
                logger.info("Loading system-level observations (no facility)")

            rows = self.load_data(options)
            logger.info("Loaded %d rows from source", len(rows))

            if not rows:
                self.stdout.write(self.style.WARNING("No rows found in source"))
                return

            batch_size = options["batch_size"]
            validate_codes = options["validate_codes"]
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
                        data = self.process_row(row, facility, validate_codes)
                        slug_value = data["slug_value"]

                        self.create_observation_definition(data, facility, None)

                        successful.append(slug_value)
                        output_rows.append(
                            {
                                "title": data["title"],
                                "slug_value": slug_value,
                                "status": "Success",
                                "error": "",
                                "code_substitutions": data.get("substitutions", ""),
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
                                "code_substitutions": "",
                            }
                        )

            output_path = options.get("output") or default_output_path
            if output_path:
                write_output_csv(
                    output_path,
                    output_rows,
                    ["title", "slug_value", "status", "error", "code_substitutions"],
                )

            self.stdout.write("\n=== Summary ===")
            self.stdout.write(f"Total rows: {total_rows}")
            self.stdout.write(self.style.SUCCESS(f"Successful: {len(successful)}"))
            self.stdout.write(self.style.ERROR(f"Failed: {len(failed)}"))
            self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
            self.stdout.write(
                self.style.SUCCESS("Observation definitions loaded successfully")
            )

        except Exception as e:
            logger.exception("Error in main process")
            error_message = f"Error in main process: {e}"
            self.stdout.write(self.style.ERROR(error_message))
            raise
