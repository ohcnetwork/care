import csv
import json
import os
from typing import Optional

from django.core import management
from django.core.management import BaseCommand, CommandParser

from care.users.models import District, State


class Command(BaseCommand):
    """
    Management command to load state and district data from JSON
    Usage: python manage.py load_state_data ./data/india/states-and-districts.json
    """

    help = "Loads Local Body data from a folder of JSONs"
    BASE_URL = "data/india/"
    valid_states = [
        "andaman_and_nicobar_islands",
        "andhra_pradesh",
        "arunachal_pradesh",
        "assam",
        "bihar",
        "chandigarh",
        "chhattisgarh",
        "delhi",
        "goa",
        "gujarat",
        "haryana",
        "himachal_pradesh",
        "jammu_and_kashmir",
        "jharkhand",
        "karnataka",
        "kerala",
        "ladakh",
        "madhya_pradesh",
        "maharashtra",
        "manipur",
        "meghalaya",
        "mizoram",
        "nagaland",
        "odisha",
        "puducherry",
        "punjab",
        "rajasthan",
        "sikkim",
        "tamil_nadu",
        "telangana",
        "the_dadra_and_nagar_haveli_and_daman_and_diu",
        "tripura",
        "uttarakhand",
        "uttar_pradesh",
        "west_bengal",
    ]

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("state", help="")

    def handle(self, *args, **options):

        state = options["state"]
        states = []
        if state == "all":
            states = self.valid_states
        else:
            if state not in self.valid_states:
                print("valid state options are ", self.valid_states)
                raise Exception("State not found")
            states = [state]

        for state in states:
            current_state_data = self.BASE_URL + state + "/lsg/"
            print("Processing Files From", current_state_data)
            management.call_command("load_lsg_data", current_state_data)
            management.call_command("load_ward_data", current_state_data)

