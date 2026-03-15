import json

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction

from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.users.models import User

from .fixtures import get_faker
from .fixtures.clinical import create_lab_definition_objects
from .fixtures.facilities import create_device, create_facility, create_location
from .fixtures.inventory import create_inventory_items
from .fixtures.organizations import (
    create_facility_organization,
    create_organization,
    create_role_organizations,
)
from .fixtures.patients import create_encounters, create_patients
from .fixtures.questionnaires import create_questionnaires
from .fixtures.users import create_default_users, create_facility_users


class Command(BaseCommand):
    help = "Generate test fixtures for the backend"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=1, help="Number of each type of users"
        )
        parser.add_argument(
            "--patients", type=int, default=10, help="Number of patients"
        )
        parser.add_argument(
            "--encounter", type=int, default=1, help="Number of encounters per patient"
        )
        parser.add_argument(
            "--default-password",
            type=str,
            default="Coronasafe@123",
            help="Set a default password for all users (easier for testing)",
        )
        parser.add_argument(
            "--output-json",
            type=str,
            default=None,
            help="Path to write a JSON manifest of all created fixture IDs",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    "This command should not be run in production. Exiting..."
                )
            )
            return

        self.stdout.write("Starting fixtures generation...")

        self.stdout.write("Syncing permissions and valuesets...")
        call_command("sync_permissions_roles")
        call_command("sync_valueset")

        try:
            with transaction.atomic():
                manifest = self._generate_fixtures(options)
                self.stdout.write(
                    self.style.SUCCESS(
                        "Successfully generated all fixtures in transaction!"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Transaction rolled back due to error: {e}")
            )
            raise

        if options["output_json"]:
            from pathlib import Path

            with Path(options["output_json"]).open("w") as f:
                json.dump(manifest, f, indent=2)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fixture manifest written to {options['output_json']}"
                )
            )

    def _generate_fixtures(self, options):  # noqa: PLR0915
        """Generate all the fixture data within a transaction context."""
        fake = get_faker()
        manifest = {}

        # Create superuser
        super_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "user_type": "admin",
                "is_superuser": True,
                "is_staff": True,
                "first_name": "Admin",
                "last_name": "User",
            },
        )
        if created:
            super_user.set_password("admin")
            super_user.save()

        self.stdout.write("=" * 30)
        if created:
            self.stdout.write("Superuser username: admin")
            self.stdout.write("Superuser password: admin")
        else:
            self.stdout.write(
                "Superuser 'admin' already exists, not creating a new one."
            )
        self.stdout.write("=" * 30)

        manifest["admin"] = {"username": "admin", "password": "admin"}

        # Create geo organization
        geo_organization = create_organization(fake, super_user)
        self.stdout.write(f"Created geo organization: {geo_organization.name}")
        manifest["geo_organization_id"] = str(geo_organization.external_id)

        # Create product suppliers
        for _ in range(2):
            create_organization(
                fake,
                super_user,
                org_type=OrganizationTypeChoices.product_supplier,
                name=f"Supplier {fake.company()}",
            )
        supplier = create_organization(
            fake,
            super_user,
            org_type=OrganizationTypeChoices.product_supplier,
            name=f"Supplier {fake.company()}",
        )

        # Create facility
        facility = create_facility(
            fake, super_user, geo_organization, "FACILITY WITH PATIENTS"
        )
        self.stdout.write(f"Created facility: {facility.name}")
        manifest["facility"] = {
            "id": str(facility.external_id),
            "name": facility.name,
        }

        # Create inventory items
        create_inventory_items(fake, facility, supplier)
        self.stdout.write("Created inventory items for facility")

        # Create facility organization (department)
        external_facility_organization = create_facility_organization(
            fake, super_user, facility
        )
        self.stdout.write(
            f"Created facility organization (dept): {external_facility_organization.name}"
        )
        manifest["facility_organization_id"] = str(
            external_facility_organization.external_id
        )

        # Create resource facility
        create_facility(fake, super_user, geo_organization)
        self.stdout.write("Created resource facility")

        # Create locations
        location = create_location(
            fake,
            super_user,
            facility,
            [external_facility_organization],
            mode="kind",
            form="wa",
        )
        self.stdout.write(f"Created location: {location.name}")

        # Create lab definitions
        create_lab_definition_objects(fake, facility, super_user)
        self.stdout.write("Created lab objects for facility")

        # Create beds
        manifest_locations = [
            {"id": str(location.external_id), "name": location.name}
        ]
        for i in range(1, 6):
            bed = create_location(
                fake,
                super_user,
                facility,
                [external_facility_organization],
                mode="instance",
                form="bd",
                parent=location.external_id,
                name=f"Bed {i}",
            )
            self.stdout.write(f"Created bed: {bed.name}")
            manifest_locations.append(
                {"id": str(bed.external_id), "name": bed.name}
            )
        manifest["locations"] = manifest_locations

        # Create devices
        manifest_devices = []
        for i in range(1, 6):
            device = create_device(
                fake,
                super_user,
                external_facility_organization,
                name=f"Device {i}",
            )
            self.stdout.write(f"Created device: {device.user_friendly_name}")
            manifest_devices.append(
                {"id": str(device.external_id), "name": device.user_friendly_name}
            )
        manifest["devices"] = manifest_devices

        # Create role organizations
        organizations = create_role_organizations(fake, super_user)
        for organization in organizations:
            self.stdout.write(f"Created organization: {organization.name}")

        # Create default users
        default_users = create_default_users(
            fake, super_user, external_facility_organization, geo_organization
        )

        self.stdout.write("=" * 50)
        self.stdout.write("DEFAULT USER CREDENTIALS")
        self.stdout.write("=" * 50)
        for u in default_users:
            self.stdout.write(
                f"{u['role']:<15} {u['username']:<30} {u['password']:<20}"
            )
        self.stdout.write("=" * 50)

        # Create facility users
        self.stdout.write("=" * 50)
        self.stdout.write("USER CREDENTIALS")
        self.stdout.write("=" * 50)
        self.stdout.write(f"{'ROLE':<15} {'USERNAME':<30} {'PASSWORD':<20}")
        self.stdout.write("-" * 65)

        facility_users = create_facility_users(
            fake,
            super_user,
            external_facility_organization,
            geo_organization,
            options["users"],
            options["default_password"],
        )
        for u in facility_users:
            self.stdout.write(
                f"{u['role']:<15} {u['username']:<30} {u['password']:<20}"
            )
        self.stdout.write("=" * 50)

        manifest["users"] = default_users + facility_users

        # Create patients
        patients = create_patients(
            fake, super_user, geo_organization, options["patients"]
        )

        # Create encounters
        encounters = create_encounters(
            fake,
            super_user,
            patients,
            facility,
            [external_facility_organization],
            options["encounter"],
        )

        # Build patient manifest with encounter IDs
        manifest_patients = []
        encounter_idx = 0
        for patient in patients:
            patient_data = {
                "id": str(patient.external_id),
                "name": patient.name,
                "encounters": [],
            }
            for _ in range(options["encounter"]):
                if encounter_idx < len(encounters):
                    patient_data["encounters"].append(
                        {"id": str(encounters[encounter_idx].external_id)}
                    )
                    encounter_idx += 1
            manifest_patients.append(patient_data)
        manifest["patients"] = manifest_patients

        # Create questionnaires
        create_questionnaires(facility, super_user)

        return manifest
