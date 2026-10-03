"""
Management command to load Charge Item Definitions from CSV/Google Sheets.

Usage:
    python manage.py load_charge_item_definition ./inputs/ChargeItemDefinition.csv --facility 24a071a3-07eb-442c-8457-bda417a375d3
    python manage.py load_charge_item_definition --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from care.emr.management.commands.load_emr_utils import (
    create_slug,
    ensure_category,
    normalize_title,
    read_csv_from_file,
    read_csv_from_google_sheet,
    read_csv_from_url,
    write_output_csv,
)
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.facility.models import Facility

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent
default_output_path = root_dir / "outputs" / "charge_item_definition_output.csv"


class Command(BaseCommand):
    """
    Load Charge Item Definitions from CSV or Google Sheets.

    Expected CSV columns:
    - title
    - Base Price
    - Tax Rate (optional: 5, 12, or 18)
    - category
    - description (optional)
    - status (optional, default: active)
    """

    help = "Load Charge Item Definitions from CSV or Google Sheets"

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

    def get_tax_components(self, tax_rate: str | None) -> list[dict]:
        """
        Get tax components based on tax rate.
        Returns list of monetary components for CGST and SGST.
        """
        tax_mapping = {
            "5": [
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "cgst",
                        "display": "CGST",
                    },
                    "factor": 2.5,
                    "conditions": [],
                },
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "sgst",
                        "display": "SGST",
                    },
                    "factor": 2.5,
                    "conditions": [],
                },
            ],
            "12": [
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "cgst",
                        "display": "CGST",
                    },
                    "factor": 6,
                    "conditions": [],
                },
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "sgst",
                        "display": "SGST",
                    },
                    "factor": 6,
                    "conditions": [],
                },
            ],
            "18": [
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "cgst",
                        "display": "CGST",
                    },
                    "factor": 9,
                    "conditions": [],
                },
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": "sgst",
                        "display": "SGST",
                    },
                    "factor": 9,
                    "conditions": [],
                },
            ],
        }

        if tax_rate and tax_rate in tax_mapping:
            return tax_mapping[tax_rate]

        if tax_rate:
            logger.warning("Unknown tax rate: %s", tax_rate)

        return []

    def process_row(self, row: dict, facility: Facility, created_by) -> dict:
        """
        Process a single CSV row into a ChargeItemDefinition data dict.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            # Validate required fields
            if not row.get("title"):
                raise ValueError("Missing required field: title")

            # Parse base price
            base_price_str = row.get("Base Price", "0")
            base_price_str = base_price_str.replace("₹", "").replace(",", "").strip()
            try:
                base_price = float(base_price_str)
            except (ValueError, TypeError):
                base_price = 0.0

            tax_rate = row.get("Tax Rate") or row.get("RATE") or row.get("Tax")

            # Ensure category exists (may raise exceptions)
            category_name = row.get("category", "service")
            try:
                category = ensure_category(
                    category_name, facility, "charge_item_definition", created_by
                )
            except Exception as e:
                error_message = f"Failed to ensure category '{category_name}': {e}"
                raise ValueError(error_message) from e

            price_components = [
                {
                    "monetary_component_type": "base",
                    "amount": str(base_price),
                    "conditions": [],
                }
            ]
            price_components.extend(self.get_tax_components(tax_rate))

            title = normalize_title(row["title"])
            slug_value = create_slug(title)

            return {
                "title": title,
                "slug_value": slug_value,
                "status": row.get("status", "active"),
                "description": row.get("description", f"Service: {title}"),
                "category": category,
                "price_components": price_components,
            }

        except (KeyError, ValueError) as e:
            error_message = f"Failed to process row: {e}"
            raise ValueError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error processing row: {e}"
            raise RuntimeError(error_message) from e

    def create_charge_item_definition(
        self, data: dict, facility: Facility, created_by
    ) -> ChargeItemDefinition:
        """
        Create or update a ChargeItemDefinition.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            full_slug = ChargeItemDefinition.calculate_slug_from_facility(
                str(facility.external_id), data["slug_value"]
            )

            existing = ChargeItemDefinition.objects.filter(
                title__iexact=data["title"], facility=facility
            ).first()

            if existing:
                logger.warning(
                    "Charge item definition already exists: %s", data["title"]
                )
                return existing

            charge_item = ChargeItemDefinition(
                facility=facility,
                slug=full_slug,
                title=data["title"],
                status=data["status"],
                description=data["description"],
                category=data["category"],
                price_components=data["price_components"],
                created_by=created_by,
                updated_by=created_by,
            )
            charge_item.save()
            logger.debug("Created charge item: %s", data["title"])
            return charge_item

        except Exception as e:
            error_message = (
                f"Failed to create charge item '{data.get('title', 'Unknown')}': {e}"
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
            logger.info("Loading charge items for facility: %s", facility.name)

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
                        data = self.process_row(row, facility, None)
                        slug_value = data["slug_value"]

                        self.create_charge_item_definition(data, facility, None)

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
                self.style.SUCCESS("Charge item definitions loaded successfully")
            )

        except Exception as e:
            logger.exception("Error in main process")
            error_message = f"Error in main process: {e}"
            self.stdout.write(self.style.ERROR(error_message))
            raise
