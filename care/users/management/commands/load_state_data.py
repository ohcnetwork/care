import csv
import json
import os
from typing import Optional

from django.core.management import BaseCommand, CommandParser

from care.users.models import District, State

states_to_ignore = [s.lower() for s in ["Kerala", "Lakshadweep (UT)"]]


class Command(BaseCommand):
    """
    Management command to load state and district data from JSON
    Usage: python manage.py load_state_data ./data/india/states-and-districts.json
    """

    help = "Loads Local Body data from a folder of JSONs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("json_file_path", help="path to the folder of JSONs")

    def handle(self, *args, **options):
        json_file_path = options["json_file_path"]

        data = []
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)

        for item in data:
            state_name = item["state"].strip()
            if state_name.lower() in states_to_ignore:
                print(f"Skipping {state_name}")
                continue

            districts = [d.strip() for d in item["districts"].split(",")]

            state, is_created = State.objects.get_or_create(name__iexact=state_name, defaults={"name": state_name})
            print(f"{'Created' if is_created else 'Retrieved'} {state_name}")

            for d in districts:
                _, is_created = District.objects.get_or_create(state=state, name__iexact=d, defaults={"name": d})
                print(f"{'Created' if is_created else 'Retrieved'} {state_name}")
