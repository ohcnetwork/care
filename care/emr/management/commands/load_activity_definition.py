"""
Management command to load Activity Definitions from CSV/Google Sheets.

This command loads dependencies first (specimens, observations, charge items)
before creating activity definitions.

Usage:
    python manage.py load_activity_definition <csv_file_or_url> --facility <facility_id>
    python manage.py load_activity_definition --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from care.emr.management.commands.load_emr_utils import (
    create_slug,
    ensure_category,
    normalize_title,
    parse_code,
    read_csv_from_file,
    read_csv_from_google_sheet,
    read_csv_from_url,
    validate_and_substitute_code,
    write_output_csv,
)
from care.emr.models.activity_definition import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.location import FacilityLocation
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.models.specimen_definition import SpecimenDefinition
from care.facility.models import Facility

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent
default_output_path = root_dir / "outputs" / "activity_definition_output.csv"


class Command(BaseCommand):
    """
    Load Activity Definitions from CSV or Google Sheets.

    Expected CSV columns:
    - title
    - description
    - usage (optional)
    - status (optional, default: active)
    - classification (optional, default: laboratory)
    - kind (optional, default: service_request)
    - category
    - code_system
    - code_value
    - code_display
    - body_site_system (optional)
    - body_site_code (optional)
    - body_site_display (optional)
    - observation_slugs (optional, comma-separated)
    - specimen_slugs (optional, comma-separated)
    - charge_item_slugs (optional, comma-separated)
    - locations (optional, comma-separated location names)
    - derived_from_uri (optional)
    """

    help = "Load Activity Definitions from CSV or Google Sheets"

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
        parser.add_argument(
            "--skip-dependencies",
            action="store_true",
            help="Skip loading dependencies (assume they exist)",
        )
        parser.add_argument(
            "--specimens-csv",
            type=str,
            help="CSV file for specimen definitions",
        )
        parser.add_argument(
            "--observations-csv",
            type=str,
            help="CSV file for observation definitions",
        )
        parser.add_argument(
            "--charge-items-csv",
            type=str,
            help="CSV file for charge item definitions",
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

    def load_dependencies(self, facility: Facility, options):
        """Load dependencies (specimens, observations, charge items) if provided."""
        if options["skip_dependencies"]:
            logger.info("Skipping dependency loading")
            return

        logger.info("\n=== Loading Dependencies ===")

        # Load specimens
        if options.get("specimens_csv"):
            logger.info("Loading specimen definitions...")
            call_command(
                "load_specimen_definition",
                options["specimens_csv"],
                facility=str(facility.external_id),
                verbosity=options["verbosity"],
            )

        # Load observations
        if options.get("observations_csv"):
            logger.info("Loading observation definitions...")
            call_command(
                "load_observation_definition",
                options["observations_csv"],
                facility=str(facility.external_id),
                verbosity=options["verbosity"],
            )

        # Load charge items
        if options.get("charge_items_csv"):
            logger.info("Loading charge item definitions...")
            call_command(
                "load_charge_item_definition",
                options["charge_items_csv"],
                facility=str(facility.external_id),
                verbosity=options["verbosity"],
            )

    def lookup_locations(
        self, location_names: list[str], facility: Facility
    ) -> tuple[list[int], list[str]]:
        """
        Lookup location IDs by names.
        Returns (location_ids, missing_names).
        """
        if not location_names:
            return [], []

        location_ids = []
        missing = []

        for name in location_names:
            location = FacilityLocation.objects.filter(
                name__iexact=name.strip(), facility=facility
            ).first()
            if location:
                location_ids.append(location.id)
            else:
                missing.append(name)
                logger.warning("Location not found: %s", name)

        return location_ids, missing

    def process_row(
        self, row: dict, facility: Facility, validate_codes: bool, created_by
    ) -> dict:
        """
        Process a single CSV row into an ActivityDefinition data dict.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            if not row.get("title"):
                raise ValueError("Missing required field: title")

            code_value = row.get("code_value")
            code_system = row.get("code_system", "http://snomed.info/sct")
            code_display = row.get("code_display")

            # Default code for activity
            default_code = {
                "code": "71388002",
                "system": "http://snomed.info/sct",
                "display": "Procedure",
            }

            substitution_messages = []

            # Validate code if requested
            if validate_codes and code_value:
                code, sub_msg = validate_and_substitute_code(
                    code_value,
                    code_system,
                    "activity-definition-procedure-code",
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

            observation_slugs = []
            if row.get("observation_slugs"):
                observation_slugs = [
                    s.strip() for s in row["observation_slugs"].split(",") if s.strip()
                ]

            specimen_slugs = []
            if row.get("specimen_slugs"):
                specimen_slugs = [
                    s.strip() for s in row["specimen_slugs"].split(",") if s.strip()
                ]

            charge_item_slugs = []
            if row.get("charge_item_slugs"):
                charge_item_slugs = [
                    s.strip() for s in row["charge_item_slugs"].split(",") if s.strip()
                ]

            location_names = []
            if row.get("locations"):
                location_names = [
                    s.strip() for s in row["locations"].split(",") if s.strip()
                ]

            category_name = row.get("category", "laboratory")
            try:
                category = ensure_category(
                    category_name, facility, "activity_definition", created_by
                )
            except Exception as e:
                error_message = f"Failed to ensure category '{category_name}': {e}"
                raise ValueError(error_message) from e

            title = normalize_title(row["title"])
            slug_value = create_slug(title)

            return {
                "title": title,
                "slug_value": slug_value,
                "status": row.get("status", "active"),
                "description": row.get("description", ""),
                "usage": row.get("usage", ""),
                "classification": row.get("classification", "laboratory"),
                "kind": row.get("kind", "service_request"),
                "category": category,
                "code": code,
                "body_site": body_site,
                "observation_slugs": observation_slugs,
                "specimen_slugs": specimen_slugs,
                "charge_item_slugs": charge_item_slugs,
                "location_names": location_names,
                "derived_from_uri": row.get("derived_from_uri", ""),
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

    def resolve_dependencies(
        self, data: dict, facility: Facility
    ) -> tuple[dict, list[str]]:
        """
        Resolve slug references to internal IDs.
        Returns (updated_data, missing_dependencies).
        """
        missing = []

        # Resolve observation slugs
        observation_ids = []
        for slug in data["observation_slugs"]:
            full_slug = ObservationDefinition.calculate_slug_from_facility(
                str(facility.external_id), slug
            )
            obs = ObservationDefinition.objects.filter(
                slug=full_slug, facility=facility
            ).first()
            if obs:
                observation_ids.append(obs.id)
            else:
                missing.append(f"observation:{slug}")

        # Resolve specimen slugs
        specimen_ids = []
        for slug in data["specimen_slugs"]:
            full_slug = SpecimenDefinition.calculate_slug_from_facility(
                str(facility.external_id), slug
            )
            spec = SpecimenDefinition.objects.filter(
                slug=full_slug, facility=facility
            ).first()
            if spec:
                specimen_ids.append(spec.id)
            else:
                missing.append(f"specimen:{slug}")

        # Resolve charge item slugs
        charge_item_ids = []
        for slug in data["charge_item_slugs"]:
            full_slug = ChargeItemDefinition.calculate_slug_from_facility(
                str(facility.external_id), slug
            )
            charge = ChargeItemDefinition.objects.filter(
                slug=full_slug, facility=facility
            ).first()
            if charge:
                charge_item_ids.append(charge.id)
            else:
                missing.append(f"charge_item:{slug}")

        # Resolve locations
        location_ids, missing_locations = self.lookup_locations(
            data["location_names"], facility
        )
        for loc in missing_locations:
            missing.append(f"location:{loc}")

        data["observation_ids"] = observation_ids
        data["specimen_ids"] = specimen_ids
        data["charge_item_ids"] = charge_item_ids
        data["location_ids"] = location_ids

        return data, missing

    def create_activity_definition(
        self, data: dict, facility: Facility, created_by
    ) -> ActivityDefinition:
        """
        Create or update an ActivityDefinition.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            full_slug = ActivityDefinition.calculate_slug_from_facility(
                str(facility.external_id), data["slug_value"]
            )

            existing = ActivityDefinition.objects.filter(
                title__iexact=data["title"], facility=facility
            ).first()

            if existing:
                logger.warning("Activity definition already exists: %s", data["title"])
                return existing

            activity = ActivityDefinition(
                facility=facility,
                slug=full_slug,
                title=data["title"],
                status=data["status"],
                description=data["description"],
                usage=data["usage"],
                classification=data["classification"],
                kind=data["kind"],
                category=data["category"],
                code=data["code"],
                body_site=data["body_site"],
                observation_result_requirements=data["observation_ids"],
                specimen_requirements=data["specimen_ids"],
                charge_item_definitions=data["charge_item_ids"],
                locations=data["location_ids"],
                derived_from_uri=data["derived_from_uri"],
                created_by=created_by,
                updated_by=created_by,
            )
            activity.save()
            logger.debug("Created activity: %s", data["title"])
            return activity

        except Exception as e:
            error_message = (
                f"Failed to create activity '{data.get('title', 'Unknown')}': {e}"
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
            # Get facility
            facility = Facility.objects.get(external_id=options["facility"])
            logger.info("Loading activities for facility: %s", facility.name)

            # Load dependencies first
            self.load_dependencies(facility, options)

            # Load activity data
            logger.info("\n=== Loading Activity Definitions ===")
            rows = self.load_data(options)
            logger.info("Loaded %d rows from source", len(rows))

            if not rows:
                self.stdout.write(self.style.WARNING("No rows found in source"))
                return

            # Process rows in batches
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
                        data = self.process_row(row, facility, validate_codes, None)
                        slug_value = data["slug_value"]

                        data, missing = self.resolve_dependencies(data, facility)

                        if missing:
                            error_msg = f"Missing dependencies: {', '.join(missing)}"
                            logger.warning("Skipping %s: %s", data["title"], error_msg)
                            failed.append(slug_value)
                            output_rows.append(
                                {
                                    "title": data["title"],
                                    "slug_value": slug_value,
                                    "status": "Failed",
                                    "error": error_msg,
                                    "code_substitutions": data.get("substitutions", ""),
                                }
                            )
                            continue

                        self.create_activity_definition(data, facility, None)

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

            # Write output CSV
            output_path = options.get("output") or default_output_path
            if output_path:
                write_output_csv(
                    output_path,
                    output_rows,
                    ["title", "slug_value", "status", "error", "code_substitutions"],
                )

            # Print summary
            self.stdout.write("\n=== Summary ===")
            self.stdout.write(f"Total rows: {total_rows}")
            self.stdout.write(self.style.SUCCESS(f"Successful: {len(successful)}"))
            self.stdout.write(self.style.ERROR(f"Failed: {len(failed)}"))
            self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
            self.stdout.write(
                self.style.SUCCESS("Activity definitions loaded successfully")
            )

        except Exception as e:
            logger.exception("Error in main process")
            error_message = f"Error in main process: {e}"
            self.stdout.write(self.style.ERROR(error_message))
            raise
