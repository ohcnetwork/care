"""
Management command to load Charge Item Definitions from CSV/Google Sheets.

Usage:
    python manage.py load_hmis_charge_item <csv_file_or_url> --facility <facility_id>
    python manage.py load_hmis_charge_item --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from care.emr.management.commands.load_emr_utils import (
    create_slug,
    ensure_category,
    load_data,
    normalize_title,
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
    - title (required)
    - slug (optional, unique identifier - if not provided, generated from title)
    - chargeitem_category (required, category name for the charge item)
    - status (optional, default: active)
    - description (optional)
    - purpose (optional)
    - base_price (required, numeric - base price amount)
    - mrp (optional, numeric - MRP amount)
    - purchase_price (optional, numeric - purchase price amount)
    - taxes_applicable (optional, e.g., "CGST 9%" or "CGST 9%, SGST 9%")

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
            default="Charge Item",
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

    def parse_price(self, value) -> str | None:
        """Parse price value to string (for JSON), return None if invalid."""
        if value is None or value == "":
            return None
        try:
            val = float(str(value).strip())
            return f"{val:.2f}"
        except (ValueError, TypeError):
            return None

    def parse_taxes_applicable(self, value) -> list:
        """
        Parse taxes_applicable string like "CGST 9%" or "CGST 9%, SGST 9%".
        Returns list of dicts with tax_type and percentage.
        """
        import re

        if not value or not str(value).strip():
            return []

        taxes = []
        # Split by comma for multiple taxes
        tax_parts = str(value).split(",")

        for part in tax_parts:
            part = part.strip()
            if not part:
                continue

            # Match patterns like "CGST 9%", "SGST 9.5%", "IGST 18%"
            match = re.match(r"(\w+)\s+([\d.]+)%?", part, re.IGNORECASE)
            if match:
                tax_type = match.group(1).lower()  # cgst, sgst, igst
                percentage = match.group(2)
                taxes.append(
                    {
                        "type": tax_type,
                        "factor": f"{float(percentage):.2f}",
                        "display": match.group(1).upper(),  # CGST, SGST, IGST
                    }
                )

        return taxes

    def build_price_components(self, row: dict) -> list:
        """
        Build price_components array from CSV row.
        Structure matches the expected API payload format.
        """
        price_components = []

        # Base price (required)
        base_price = self.parse_price(row.get("base_price"))
        if base_price:
            price_components.append(
                {
                    "monetary_component_type": "base",
                    "amount": base_price,
                    "conditions": [],
                }
            )

        # MRP (informational)
        mrp = self.parse_price(row.get("mrp"))
        if mrp:
            price_components.append(
                {
                    "monetary_component_type": "informational",
                    "amount": mrp,
                    "code": {
                        "system": "http://ohc.network/codes/monetary/informational",
                        "version": None,
                        "code": "mrp",
                        "display": "MRP",
                    },
                    "conditions": [],
                }
            )

        # Purchase price (informational)
        purchase_price = self.parse_price(row.get("purchase_price"))
        if purchase_price:
            price_components.append(
                {
                    "monetary_component_type": "informational",
                    "amount": purchase_price,
                    "code": {
                        "system": "care",
                        "code": "purchase_price",
                        "display": "Purchase Price",
                    },
                    "conditions": [],
                }
            )

        # Parse taxes from taxes_applicable column
        taxes = self.parse_taxes_applicable(row.get("taxes_applicable"))
        for tax in taxes:
            price_components.append(
                {
                    "monetary_component_type": "tax",
                    "code": {
                        "system": "http://ohc.network/codes/monetary/tax",
                        "code": tax["type"],
                        "display": tax["display"],
                    },
                    "factor": tax["factor"],
                    "amount": None,
                    "conditions": [],
                }
            )

        return price_components

    def process_row(self, row: dict, facility: Facility, created_by) -> dict:
        """
        Process a single CSV row into a ChargeItemDefinition data dict.
        Raises exceptions with descriptive messages on errors.
        """
        try:
            if not row.get("title"):
                raise ValueError("Missing required field: title")

            if not row.get("chargeitem_category"):
                raise ValueError("Missing required field: chargeitem_category")

            # Ensure category exists using chargeitem_category name
            category_name = row["chargeitem_category"].strip()
            try:
                category = ensure_category(
                    category_name,
                    facility,
                    "charge_item_definition",
                    created_by,
                )
            except Exception as e:
                error_message = f"Failed to ensure category '{category_name}': {e}"
                raise ValueError(error_message) from e

            title = normalize_title(row["title"])
            slug_value = row.get("slug") or create_slug(title, ensure_unique=True)

            # Build price_components array
            price_components = self.build_price_components(row)

            return {
                "title": title,
                "slug_value": slug_value,
                "category": category,
                "status": (row.get("status") or "").strip() or "active",
                "description": row.get("description", ""),
                "purpose": row.get("purpose", ""),
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

            # Check for existing by slug (unique identifier)
            existing = ChargeItemDefinition.objects.filter(
                slug=full_slug, facility=facility
            ).first()

            if existing:
                logger.warning(
                    "Charge item definition already exists with slug: %s (title: %s)",
                    data["slug_value"],
                    data["title"],
                )
                return existing

            charge_item = ChargeItemDefinition(
                facility=facility,
                slug=full_slug,
                title=data["title"],
                status=data["status"],
                category=data["category"],
                description=data["description"],
                purpose=data["purpose"],
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

            rows = load_data(options)
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
