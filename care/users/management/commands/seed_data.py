from django.core.management import BaseCommand
from care.users.fixtures import UserFixture, users, skills, user_skills

class Command(BaseCommand):
    """
    Seeds the database with dummy data.
    """

    help = "Seed Data"

    def handle(self, *args, **options):
        UserFixture(users, skills, user_skills).load()
        self.stdout.write(self.style.SUCCESS("Seed Data Complete"))
        return 0
