import runpy
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "fixtures" / "scripts" / "default_fixtures.py"
)


class Command(BaseCommand):
    help = "Load fixture data for local development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_FIXTURE_PATH),
            help=(
                "Path to a fixture script. The file's top-level code is "
                "executed; it is responsible for opening its own "
                "`care_fixture_context()`. Defaults to the bundled "
                "care/fixtures/scripts/default_fixtures.py."
            ),
        )

    def handle(self, *args, path, **options):
        if settings.IS_PRODUCTION:
            msg = "This command should not be run in production. Exiting..."
            self.stderr.write(self.style.ERROR(msg))
            raise CommandError(msg)

        script_path = Path(path).expanduser().resolve()
        if not script_path.is_file():
            message = f"Fixture script not found: {script_path}"
            raise CommandError(message)

        self.stdout.write(
            self.style.WARNING(f"\nStarting fixtures from {script_path}\n")
        )

        runpy.run_path(str(script_path), run_name="__main__")

        self.stdout.write(self.style.SUCCESS("\nAll fixtures loaded successfully!\n"))
