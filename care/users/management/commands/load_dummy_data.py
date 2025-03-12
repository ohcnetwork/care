from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("I'm sorry boss, I dont have any dummy data")  # noqa T201
