import json

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction

from .fixtures import FixtureContext, get_faker
from .fixtures.clinical import setup_clinical
from .fixtures.facilities import setup_facility
from .fixtures.inventory import setup_inventory
from .fixtures.organizations import setup_organizations
from .fixtures.patients import setup_patients
from .fixtures.questionnaires import setup_questionnaires
from .fixtures.users import setup_admin, setup_users


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

    def _generate_fixtures(self, options):
        """Generate all fixture data within a transaction context.

        Each setup_* function reads what it needs from the context and
        writes back what it produces.  Adding a new fixture domain is:
          1. Create fixtures/<domain>.py with a setup_<domain>(ctx) function
          2. Add one line here calling it in the right order
        """
        ctx = FixtureContext(
            fake=get_faker(),
            super_user=None,  # set by setup_admin
            options=options,
            write=self.stdout.write,
        )

        # Core infrastructure (order matters — later steps depend on earlier ones)
        setup_admin(ctx)
        setup_organizations(ctx)
        setup_facility(ctx)

        # Domain data (depend on facility + organizations)
        setup_inventory(ctx)
        setup_clinical(ctx)
        setup_users(ctx)
        setup_patients(ctx)
        setup_questionnaires(ctx)

        return ctx.manifest
