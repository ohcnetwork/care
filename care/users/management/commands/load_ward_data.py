import glob
import json

from django.core.management.base import BaseCommand, CommandParser
from django.db import IntegrityError

from care.users.models import LOCAL_BODY_CHOICES, District, LocalBody, Ward


class Command(BaseCommand):
    """
    Management command to load ward information from a folder of JSONs
    Sample data: https://github.com/rebuildearth/data/tree/master/data/india/kerala/lsgi_site_data
    """

    help = "Loads Local Body data from a folder of JSONs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("folder", help="path to the folder of JSONs")

    def handle(self, *args, **options) -> str | None:
        def int_or_zero(value):
            try:
                int(value)
                return value
            except ValueError:
                return 0

        def get_ward_number(ward):
            if "ward_number" in ward:
                return int_or_zero(ward["ward_number"])
            return int_or_zero(ward["ward_no"])

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
            if not lb["district"]:
                return None
            return LocalBody.objects.filter(
                name=lb["name"],
                district=district_map[lb["district"]],
                localbody_code=lb.get("localbody_code"),
                body_type=LOCAL_BODY_CHOICE_MAP.get(
                    (lb.get("localbody_code", " "))[0],
                    LOCAL_BODY_CHOICES[-1][0],
                ),
            ).first()

        for f in sorted(glob.glob(f"{folder}/*.json")):
            with open(f"{f}") as data_f:
                data = json.load(data_f)
                wards = data.pop("wards", None)
                if wards is None:
                    print("Ward Data not Found ")
                if data.get("district") is not None:
                    local_body = get_local_body(data)
                    if not local_body:
                        continue
                    wards.sort(key=lambda x: get_ward_name(x) + str(get_ward_number(x)))
                    for ward in wards:
                        counter += 1
                        try:
                            obj = Ward(
                                local_body=local_body,
                                number=get_ward_number(ward),
                                name=get_ward_name(ward),
                            )
                            obj.save()
                        except IntegrityError:
                            pass
        print("Processed ", str(counter), " wards")
