"""
Management command to load HMIS Users from CSV/Google Sheets.

Usage:
    python manage.py load_hmis_users <csv_file_or_url> --facility <facility_id>
    python manage.py load_hmis_users --google-sheet <sheet_id> --sheet-name <name> --facility <facility_id>
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.management.commands.load_emr_utils import (
    load_data,
    set_logger_level,
    write_output_csv,
)
from care.emr.models import Organization
from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.facility.models import Facility
from care.security.models import RoleModel
from care.users.models import User

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent.parent.parent
default_output_path = root_dir / "outputs" / "hmis_users_output.csv"


class Command(BaseCommand):
    """
    Load HMIS Users from CSV or Google Sheets.

    Expected CSV columns (required):
    - user_type (e.g., nurse, doctor, staff)
    - username
    - password
    - first_name
    - last_name
    - email
    - phone_number
    - gender (male, female, non_binary, transgender)

    Optional CSV columns:
    - prefix (e.g., Dr., Mr., Ms.)
    - suffix
    - geo_organization (UUID of government organization)
    - department_name (name of department(s) in facility, comma-separated for multiple, e.g., "Anesthesia,OBG,Medicine")
    - sub_department_name (name of sub-department(s), comma-separated to match department order if provided)
    - role_name (name of role for facility department link, applies to all departments)
    """

    help = "Load HMIS Users from CSV or Google Sheets"

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
            default="User Creation",
            help="Sheet name (default: User Creation)",
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

    def validate_row(self, row: dict) -> list[str]:
        """
        Validate required fields in a row.
        Returns list of missing field names.
        """
        required_fields = [
            "user_type",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "gender",
        ]
        missing = []
        for field in required_fields:
            if not row.get(field):
                missing.append(field)
        return missing

    def process_row(self, row: dict) -> dict:
        print(row)
        """
        Process a single CSV row into a User data dict.
        Raises exceptions with descriptive messages on errors.
        """
        # Validate required fields
        missing_fields = self.validate_row(row)
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        user_type = row.get("user_type", "").strip()

        # Validate gender
        valid_genders = ["male", "female", "non_binary", "transgender"]
        gender = row.get("gender", "").lower()
        if gender not in valid_genders:
            raise ValueError(
                f"Invalid gender: {gender}. Must be one of: {valid_genders}"
            )

        # Process phone number - add +91 prefix if not present
        phone_number = row["phone_number"].strip()
        if not phone_number.startswith("+"):
            phone_number = f"+91{phone_number}"

        # Build user data dict
        user_data = {
            "user_type": user_type,
            "username": row["username"].strip(),
            "password": row["password"],
            "first_name": row["first_name"].strip(),
            "last_name": row["last_name"].strip(),
            "email": row["email"].strip().lower(),
            "phone_number": phone_number,
            "gender": gender,
            "is_service_account": False,
        }

        # Optional fields
        if row.get("prefix"):
            user_data["prefix"] = row["prefix"].strip()
        if row.get("suffix"):
            user_data["suffix"] = row["suffix"].strip()
        if row.get("geo_organization"):
            user_data["geo_organization_id"] = row["geo_organization"].strip()

        # Facility linking fields (comma-separated for multiple departments)
        if row.get("department_name"):
            dept_names = [
                d.strip() for d in row["department_name"].split(",") if d.strip()
            ]
            if dept_names:
                user_data["department_name"] = dept_names
        if row.get("sub_department_name"):
            sub_dept_names = [s.strip() for s in row["sub_department_name"].split(",")]
            # Preserve empty strings to maintain index alignment with departments
            user_data["sub_department_name"] = sub_dept_names
        if row.get("role_name"):
            user_data["role_name"] = row["role_name"].strip()

        return user_data

    def create_user(self, data: dict, facility: Facility) -> User:
        """
        Create a User and associate with role organization.
        Raises exceptions with descriptive messages on errors.
        """
        with transaction.atomic():
            # Get geo_organization if provided
            geo_organization = None
            if data.get("geo_organization_id"):
                geo_organization = Organization.objects.filter(
                    external_id=data["geo_organization_id"],
                    org_type="govt",
                ).first()
                if not geo_organization:
                    logger.warning(
                        "Geo organization not found: %s", data["geo_organization_id"]
                    )

            user = User.objects.filter(username=data["username"]).first()
            if not user:
                # Check if email already exists
                if User.objects.filter(email=data["email"]).exists():
                    raise ValueError(f"Email '{data['email']}' already exists")

                # Check if phone_number already exists
                if User.objects.filter(phone_number=data["phone_number"]).exists():
                    raise ValueError(
                        f"Phone number '{data['phone_number']}' already exists"
                    )
                # Create the user
                user = User(
                    username=data["username"],
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    email=data["email"],
                    phone_number=data["phone_number"],
                    gender=data["gender"],
                    user_type=data["user_type"],
                    is_service_account=data["is_service_account"],
                    prefix=data.get("prefix", ""),
                    suffix=data.get("suffix", ""),
                    geo_organization=geo_organization,
                )
                user.set_password(data["password"])
                user.save()

            # Link user to facility department(s) with role
            if data.get("department_name") and data.get("role_name"):
                facility_role = RoleModel.objects.filter(
                    name__iexact=data["role_name"]
                ).first()
                if not facility_role:
                    raise ValueError(f"Role '{data['role_name']}' not found")

                department_names = data["department_name"]
                sub_department_names = data.get("sub_department_name", [])

                for idx, dept_name in enumerate(department_names):
                    department = FacilityOrganization.objects.filter(
                        facility=facility, name__iexact=dept_name
                    ).first()
                    if not department:
                        raise ValueError(
                            f"Department '{dept_name}' not found in facility"
                        )

                    # Determine target organization (sub-department or department)
                    target_organization = department

                    # Check if there's a corresponding sub-department
                    if idx < len(sub_department_names):
                        sub_dept_name = sub_department_names[idx].strip()
                        if sub_dept_name:
                            sub_department = FacilityOrganization.objects.filter(
                                facility=facility,
                                parent=department,
                                name__iexact=sub_dept_name,
                            ).first()
                            if not sub_department:
                                raise ValueError(
                                    f"Sub-department '{sub_dept_name}' not found "
                                    f"under department '{dept_name}'"
                                )
                            target_organization = sub_department

                    org_name = target_organization.name
                    self.stdout.write(
                        f"Linking user {data['username']} to {org_name} with role {data['role_name']}"
                    )

                    FacilityOrganizationUser.objects.get_or_create(
                        organization=target_organization,
                        user=user,
                        role=facility_role,
                    )
                    logger.debug(
                        "Linked user %s to organization %s with role %s",
                        data["username"],
                        org_name,
                        data["role_name"],
                    )

            logger.debug("Created user: %s", data["username"])
            return user

    def handle(self, *args, **options):
        start_time = datetime.now(tz=UTC)

        # Set logging level
        set_logger_level(logger, options.get("verbosity", 1))

        try:
            # Get facility
            facility = Facility.objects.get(external_id=options["facility"])
            logger.info("Loading users for facility: %s", facility.name)

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
                    row_username = row.get("username", "Unknown")

                    try:
                        data = self.process_row(row)
                        self.create_user(data, facility)

                        successful.append(row_username)
                        output_rows.append(
                            {
                                "username": row_username,
                                "email": data.get("email", ""),
                                "status": "Success",
                                "error": "",
                            }
                        )

                    except Exception as e:
                        logger.error("Error processing row '%s': %s", row_username, e)
                        failed.append(row_username)
                        output_rows.append(
                            {
                                "username": row_username,
                                "email": row.get("email", ""),
                                "status": "Failed",
                                "error": str(e),
                            }
                        )

            output_path = options.get("output") or default_output_path
            if output_path:
                write_output_csv(
                    output_path,
                    output_rows,
                    ["username", "email", "status", "error"],
                )

            self.stdout.write("\n=== Summary ===")
            self.stdout.write(f"Total rows: {total_rows}")
            self.stdout.write(self.style.SUCCESS(f"Successful: {len(successful)}"))
            self.stdout.write(self.style.ERROR(f"Failed: {len(failed)}"))
            self.stdout.write(f"Time taken: {datetime.now(tz=UTC) - start_time}")
            self.stdout.write(self.style.SUCCESS("HMIS users loaded successfully"))

        except Exception as e:
            logger.exception("Error in main process")
            error_message = f"Error in main process: {e}"
            self.stdout.write(self.style.ERROR(error_message))
            raise
