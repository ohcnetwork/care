from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """ """

    help = "Migrate Facility Organizations."

    def handle(self, *args, **options):
        # Create default facility organization for each Facility
        # Move users into that organization based on Facility Users
        # All encounters in that facility will be attached this organization
        pass
