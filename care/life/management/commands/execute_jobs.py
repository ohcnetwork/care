from django.core.management.base import BaseCommand

from care.life.tasks.job_executor import run_jobs


class Command(BaseCommand):
    """
    Management command to Force run Jobs.
    """

    help = "Force run jobs"

    def handle(self, *args, **options):
        run_jobs()

