import glob
import json
from typing import Optional

from django.core.management.base import BaseCommand, CommandParser

from care.users.models import LOCAL_BODY_CHOICES, District, LocalBody, Block

from django.db import IntegrityError


class Command(BaseCommand):
    """
    Management command to load block information from a folder of JSONs
    """

    help = "Loads Local Body data from a folder of JSONs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("folder", help="path to the folder of JSONs")

    def handle(self, *args, **options) -> Optional[str]:
        def int_or_zero(value):
            try:
                int(value)
                return value
            except:
                return 0

        folder = options["folder"]
        counter = 0

        districts = District.objects.all()
        district_map = {d.name: d for d in districts}

        for f in glob.glob(f"{folder}/blocks/blocks*.json"):
            with open(f"{f}", "r") as data_f:
                data = json.load(data_f)
                blocks = data.pop("blocks", None)
                if blocks is None:
                    print("Block Data not Found ")
                for block in blocks:
                    counter += 1
                    try:
                        if district_map.get(block["district"], None) is None:
                            print("district ", block["district"]," doesn't exist")
                        obj = Block(district=district_map[block["district"]], number=int_or_zero(block["number"]), name=block["name"])
                        obj.save()
                    except IntegrityError as e:
                        pass
        print("Processed ", str(counter), " blocks")

