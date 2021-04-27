from django.core.management.base import BaseCommand

from care.life.tasks.job_executor import save_life_data


class Command(BaseCommand):
    """
    Management command to Force Save Life Data.
    """

    help = "Force Save Life Data Objects"

    def handle(self, *args, **options):
        save_life_data()

