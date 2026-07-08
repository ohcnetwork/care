"""Management command to publish the Care catalog to the network.

Examples::

    # Preview the catalog that would be published (no network call):
    python manage.py publish_beckn_catalog --dry-run

    # Publish only public schedules (default) to the configured BPP caller:
    python manage.py publish_beckn_catalog

    # Publish every schedule (including non-public), e.g. for testing:
    python manage.py publish_beckn_catalog --all
"""

import json

from django.core.management.base import BaseCommand

from care.beckn.services.publisher import publish_catalog


class Command(BaseCommand):
    help = "Publish the Care catalog (facilities + practitioner availability) to the network via the BPP caller."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build and print the catalog payload without POSTing it.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Include non-public schedules (default: public schedules only).",
        )
        parser.add_argument(
            "--coordination",
            action="store_true",
            help=(
                "Publish the Care-coordinator ('front desk') "
                "ServiceCoordinationResource catalog instead of the facility "
                "HealthResource catalogs."
            ),
        )

    def handle(self, *args, **options):
        public_only = not options["all"]
        result = publish_catalog(
            public_only=public_only,
            dry_run=options["dry_run"],
            coordination=options["coordination"],
        )
        if result["status"] == "dry_run":
            self.stdout.write(json.dumps(result["payload"], indent=2, default=str))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run: {result['catalogs']} catalog(s) built (not published)."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Published {result['catalogs']} catalog(s) to {result['url']} "
                f"(HTTP {result['http_status']})."
            )
        )
