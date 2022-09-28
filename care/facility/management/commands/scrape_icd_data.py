from django.core.management.base import BaseCommand

from care.facility.tasks.icd.scraper import ICDScraper


class Command(BaseCommand):
    """
    Management command to scrape ICD11 Disease Data
    """

    help = "Dump ICD11 Data to Json"

    def handle(self, *args, **options):
        scraper = ICDScraper()
        scraper.scrape()
