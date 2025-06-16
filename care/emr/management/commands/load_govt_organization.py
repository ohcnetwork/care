import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.models.organization import Organization

logger = logging.getLogger(__name__)


local_body_choice_map = {
    "G": "grama_panchayat",
    "B": "block_panchayat",
    "D": "district_panchayat",
    "N": "nagar_panchayat",
    "M": "municipality",
    "C": "corporation",
    "O": "other_local_body",
}

state_cache = {}
districts_cache = defaultdict(dict)


def get_state(state_name):
    if state_name not in state_cache:
        try:
            state_cache[state_name] = Organization.objects.get(
                name=state_name, root_org=None
            )
        except Organization.DoesNotExist:
            logger.error("State not found: '%s'", state_name)
            state_cache[state_name] = None
            # raise e
    return state_cache[state_name]


def get_district(state_name, district_name):
    state = get_state(state_name)
    if not state:
        return None
    if district_name not in districts_cache[state_name]:
        try:
            districts_cache[state_name][district_name] = Organization.objects.get(
                name=district_name, parent=state
            )
        except Organization.DoesNotExist:
            logger.error(
                "District not found: %s, '%s'",
                state_name,
                district_name,
            )
            districts_cache[state_name][district_name] = None
            # raise e
    return districts_cache[state_name][district_name]


def get_local_body(state_name, district_name, local_body_name):
    district = get_district(state_name, district_name)
    if not district:
        return None
    try:
        return Organization.objects.filter(
            name=local_body_name, parent=district
        ).first()
    except Organization.DoesNotExist:
        logger.error(
            "Local Body not found: %s, %s, '%s'",
            state_name,
            district_name,
            local_body_name,
        )
        # raise e


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


def get_local_body_name(local_body):
    return local_body["name"].replace("  ", " ").replace("\n", "")  # noqa: RUF001


class Command(BaseCommand):
    """ """

    help = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.migration_id = int(datetime.now(tz=UTC).timestamp() * 1000)
        self.country = "India"

    def add_arguments(self, parser):
        parser.add_argument(
            "--state",
            default="all",
            help="State to load data for. If 'all', data for all states will be loaded",
        )
        parser.add_argument(
            "--load-districts",
            default=False,
            action="store_true",
            help="Load district data",
        )
        parser.add_argument(
            "--load-local-bodies",
            default=False,
            action="store_true",
            help="Load local body data",
        )
        parser.add_argument(
            "--load-wards",
            default=False,
            action="store_true",
            help="Load ward data",
        )

    def load_state_and_district_data(self):
        with self.json_file_path.open() as json_file:
            data = json.load(json_file)

        state_defaults = {
            "active": True,
            "org_type": "govt",
            "description": "",
            "has_children": True,
            "system_generated": True,
            "level_cache": 0,
            "metadata": {
                "country": self.country,
                "govt_org_type": "state",
                "govt_org_children_type": "district",
            },
            "meta": {
                "migration_id": self.migration_id,
            },
        }

        if self.state != "all":
            data = [d for d in data if d["slug"] == self.state]

        for item in data:
            state_name = item["state"].strip()

            districts = [d.strip() for d in item["districts"].split(",")]

            state, created = Organization.objects.get_or_create(
                name__iexact=state_name,
                metadata__govt_org_type="state",
                defaults={**state_defaults, "name": state_name},
            )
            state_cache[state_name] = state
            if not created:
                logger.debug("State already exists: %s (%s)", state.name, state.id)
            else:
                logger.debug("Created state: %s (%s)", state.name, state.id)

            district_defaults = {
                "root_org": state,
                "parent": state,
                "org_type": "govt",
                "description": "",
                "has_children": True,
                "system_generated": True,
                "level_cache": 1,
                "metadata": {
                    "country": self.country,
                    "govt_org_type": "district",
                    "govt_org_children_type": "local_body",
                },
                "meta": {
                    "migration_id": self.migration_id,
                },
            }

            if not self.load_districts:
                continue

            for d in districts:
                district, created = Organization.objects.get_or_create(
                    parent=state,
                    name__iexact=d,
                    defaults={
                        **district_defaults,
                        "name": d,
                    },
                )
                districts_cache[state_name][d] = district
                district.get_parent_json()
                if not created:
                    logger.debug(
                        "District already exists: %s (%s)", district.name, district.id
                    )
                else:
                    logger.debug(
                        "Created district: %s (%s)", district.name, district.id
                    )

    def load_local_bodies_data(self, state_dirs: list[Path]):
        def create_local_bodies(local_body_list):
            local_body_list.sort(
                key=lambda lb: (
                    lb["name"],
                    lb.get("localbody_code", ""),
                )
            )
            local_body_objs = []
            for local_body in local_body_list:
                if not local_body["district"]:
                    continue
                dist_obj: Organization = get_district(
                    local_body["state"], local_body["district"]
                )
                if not dist_obj:
                    continue
                local_body_objs.append(
                    Organization(
                        root_org=dist_obj.parent,
                        name=get_local_body_name(local_body),
                        parent=dist_obj,
                        org_type="govt",
                        level_cache=2,
                        system_generated=True,
                        metadata={
                            "country": self.country,
                            "govt_org_type": "local_body",
                            "govt_org_children_type": "ward",
                            "govt_org_id": local_body.get(
                                "lsg_code", local_body.get("localbody_code")
                            ),
                        },
                        meta={
                            "migration_id": self.migration_id,
                        },
                    )
                )
            count = Organization.objects.bulk_create(local_body_objs)
            logger.debug("Created %s local bodies", len(count))

        for state_dir in state_dirs:
            local_bodies = []
            for counter, f in enumerate((state_dir / "lsg").glob("*.json")):
                with f.open() as data_f:
                    data = json.load(data_f)
                    data.pop("wards", None)
                    local_bodies.append(data)
                if counter % 3000 == 0:
                    create_local_bodies(local_bodies)
                    local_bodies = []
            create_local_bodies(local_bodies)

    def load_wards_data(self, state_dirs: list[Path]):
        for state_dir in state_dirs:
            for f in sorted((state_dir / "lsg").glob("*.json")):
                with f.open() as data_f:
                    data = json.load(data_f)
                    wards = data.pop("wards", None)
                    if not wards:
                        logger.info("Ward Data not Found for %s", f)
                        continue
                    if data.get("district") is not None:
                        local_body = get_local_body(
                            data["state"], data["district"], get_local_body_name(data)
                        )
                        if not local_body:
                            continue
                        wards.sort(
                            key=lambda x: get_ward_name(x) + str(get_ward_number(x))
                        )
                        ward_objs = []
                        for ward in wards:
                            ward_objs.append(
                                Organization(
                                    root_org=local_body.root_org,
                                    parent=local_body,
                                    name=get_ward_name(ward),
                                    org_type="govt",
                                    system_generated=True,
                                    level_cache=3,
                                    metadata={
                                        "country": self.country,
                                        "govt_org_type": "ward",
                                        "govt_org_id": get_ward_number(ward),
                                    },
                                    meta={
                                        "migration_id": self.migration_id,
                                    },
                                )
                            )
                        count = Organization.objects.bulk_create(ward_objs)
                        logger.debug("Created %s wards", len(count))

    def handle(self, *args, **options):
        if options["verbosity"] == 0:
            logger.setLevel(logging.ERROR)
        elif options["verbosity"] == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        self.json_file_path: Path = (
            settings.BASE_DIR / "data/india/states-and-districts.json"
        )
        self.state = options["state"]
        self.load_districts = options["load_districts"]
        self.load_local_bodies = options["load_local_bodies"]
        self.load_wards = options["load_wards"]

        logger.info("Loading Govt Organization Data")
        logger.info("Migration ID: %s", self.migration_id)

        logger.info("Loading State and District Data")
        with transaction.atomic():
            self.load_state_and_district_data()

            root_dir: Path = settings.BASE_DIR / "data/india"

            if self.state != "all":
                state_dirs = [root_dir / self.state]
            else:
                state_dirs = [d for d in root_dir.iterdir() if d.is_dir()]

            if self.load_districts:
                if self.load_local_bodies:
                    logger.info("Loading Local Body Data")
                    self.load_local_bodies_data(state_dirs)
                if self.load_wards:
                    logger.info("Loading Ward Data")
                    self.load_wards_data(state_dirs)

        logger.info("Data Loaded")
