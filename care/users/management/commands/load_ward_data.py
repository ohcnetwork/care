import glob
import json
from typing import Optional

from django.core.management.base import BaseCommand, CommandParser

from care.users.models import LOCAL_BODY_CHOICES, District, LocalBody, Ward

from django.db import IntegrityError


class Command(BaseCommand):
    """
    Management command to load ward information from a folder of JSONs
    Sample data: https://github.com/rebuildearth/data/tree/master/data/india/kerala/lsgi_site_data
    """

    help = "Loads Local Body data from a folder of JSONs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("folder", help="path to the folder of JSONs")

    def handle(self, *args, **options) -> Optional[str]:
        def get_ward_number(ward):
            if "ward_number" in ward:
                return ward["ward_number"]
            return ward["ward_no"]

        def get_ward_name(ward):
            if "ward_name" in ward:
                return ward["ward_name"]
            return ward["name"]

        folder = options["folder"]
        counter = 0

        districts = District.objects.all()
        district_map = {d.name: d for d in districts}

        # Creates a map with first char of readable value as key
        LOCAL_BODY_CHOICE_MAP = dict([(c[1][0], c[0]) for c in LOCAL_BODY_CHOICES])

        def get_local_body(lb):

            return LocalBody.objects.get(
                name=lb["name"],
                district=district_map[lb["district"]],
                localbody_code=lb.get("localbody_code"),
                body_type=LOCAL_BODY_CHOICE_MAP.get((lb.get("localbody_code", " "))[0], LOCAL_BODY_CHOICES[-1][0]),
            )

        for f in glob.glob(f"{folder}/*.json"):
            with open(f"{f}", "r") as data_f:
                data = json.load(data_f)
                wards = data.pop("wards", None)
                if wards is None:
                    print("Ward Data not Found ")
                if data.get("district") is not None:
                    local_body = get_local_body(data)
                    for ward in wards:
                        counter += 1
                        try:
                            obj = Ward(local_body=local_body, number=get_ward_number(ward), name=get_ward_name(ward))
                            obj.save()
                        except IntegrityError as e:
                            print(e)
        print("Processed ", str(counter), " wards")

