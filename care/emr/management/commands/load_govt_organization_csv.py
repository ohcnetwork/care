import logging
from csv import DictReader
from datetime import UTC, datetime
from typing import NamedTuple

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from care.emr.models import Organization

logger = logging.getLogger(__name__)


class RowObj(NamedTuple):
    state: str
    district: str
    local_body: str
    local_body_type: str
    grama_panchayat: str
    ward_number: int
    ward_name: str


type OrgDict = dict[
    str,  # state
    dict[
        str,  # district
        dict[
            str,  # local_body
            dict[
                str,  # local_body_type
                dict[
                    int,  # ward_number
                    str,  # ward_name
                ]
                | dict[  # if local_body_type is block_panchayat
                    str,  # grama_panchayat
                    dict[
                        int,  # ward_number
                        str,  # ward_name
                    ],
                ],
            ],
        ],
    ],
]


class Command(BaseCommand):
    """
    Load Govt Organizations from CSV
    The script takes in a CSV file with the following columns:
    - State
    - District
    - Local Body
    - Local Body Type
    - Grama Panchayat
    - Ward Number
    - Ward Name
    """

    help = "Load Govt Organizations from CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_file_url", type=str, help="CSV File URL")

    def read_csv(self, url: str) -> list[RowObj]:
        logger.info("Reading CSV from %s", url)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = set()
        duplicates = []
        logger.info("Parsing CSV")
        reader = DictReader(response.text.splitlines())
        expected_columns = {
            "State",
            "District",
            "Local Body",
            "Local Body Type",
            "Grama Panchayat",
            "Ward Number",
            "Ward Name",
        }
        if not expected_columns.issubset(reader.fieldnames):
            logger.error("Invalid CSV Columns: %s", reader.fieldnames)
            raise ValueError("Invalid CSV Columns")
        for row in DictReader(response.text.splitlines()):
            row_obj = RowObj(
                state=row["State"].strip(),
                district=row["District"].strip(),
                local_body=row["Local Body"].strip(),
                local_body_type=row["Local Body Type"]
                .strip()
                .lower()
                .replace(" ", "_"),
                grama_panchayat=row["Grama Panchayat"].strip(),
                ward_number=int(row["Ward Number"].strip()),
                ward_name=row["Ward Name"].strip(),
            )
            if row_obj in data:
                duplicates.append(row_obj)
            data.add(row_obj)
        if duplicates:
            logger.error("Duplicate rows found: %s", duplicates)
            raise ValueError("Duplicate rows found")
        logger.info("Sorting Data")
        sorted_data = sorted(
            data,
            key=lambda x: (
                x.state,
                x.district,
                x.local_body,
                x.local_body_type,
                x.grama_panchayat,
                x.ward_number,
            ),
        )
        logger.info("Rows Parsed: %s", len(sorted_data))
        return sorted_data

    def rows_to_dict(self, rows: list[RowObj]) -> OrgDict:
        # convert rows to nested dict
        logger.info("Converting Rows to Dict")
        data = {}
        count = 0
        for row in rows:
            if not all(
                [
                    row.state,
                    row.district,
                    row.local_body,
                    row.local_body_type,
                    row.ward_number,
                    row.ward_name,
                ]
            ) or (row.local_body_type == "block_panchayat" and not row.grama_panchayat):
                logger.error("Invalid Row: %s", row)
                # raise ValueError("Invalid Row") # TODO: uncomment when we have clean data
                continue
            state: dict = data.setdefault(row.state, {})
            district: dict = state.setdefault(row.district, {})
            local_body: dict = district.setdefault(row.local_body, {})
            local_body_type: dict = local_body.setdefault(row.local_body_type, {})
            if row.local_body_type == "block_panchayat":
                grama_panchayat: dict = local_body_type.setdefault(
                    row.grama_panchayat, {}
                )
                if row.ward_number in grama_panchayat:
                    logger.error("Duplicate Ward: %s", row)
                    # raise ValueError("Duplicate Ward") # TODO: uncomment when we have clean data
                    # we cant be sure which one is correct
                    del grama_panchayat[row.ward_number]
                    count -= 1
                    continue
                grama_panchayat[row.ward_number] = row.ward_name
            else:
                if row.ward_number in local_body_type:
                    logger.error("Duplicate Ward: %s", row)
                    # raise ValueError("Duplicate Ward") # TODO: uncomment when we have clean data
                    # we cant be sure which one is correct
                    del local_body_type[row.ward_number]
                    count -= 1
                    continue
                local_body_type[row.ward_number] = row.ward_name
            count += 1
        logger.info("Rows Converted: %s", count)
        return data

    def create_ward(self, state, parent, ward_number, ward_name):
        name = f"{ward_number}: {ward_name}"
        metadata = {
            "country": self.country,
            "govt_org_type": "ward",
            "govt_org_id": ward_number,
        }
        ward_obj, created = Organization.objects.filter(
            name__iexact=name,
            parent=parent,
            org_type="govt",
            metadata=metadata,
        ).get_or_create(
            defaults={
                "name": name,
                "root_org": state,
                "parent": parent,
                "org_type": "govt",
                "system_generated": True,
                "metadata": metadata,
                "meta": {"migration_id": self.timestamp},
            },
        )
        logger.debug(
            "Ward: %s, Created: %s, Ward ID: %s",
            name,
            created,
            ward_obj.id,
        )

    def create_organization(self, data: OrgDict):
        logger.info("Creating Organizations")
        for state, districts in data.items():
            metadata = {
                "country": self.country,
                "govt_org_type": "state",
                "govt_org_children_type": "district",
            }
            state_obj, created = Organization.objects.filter(
                name__iexact=state, org_type="govt", parent=None, metadata=metadata
            ).get_or_create(
                defaults={
                    "name": state,
                    "org_type": "govt",
                    "system_generated": True,
                    "metadata": metadata,
                    "meta": {"migration_id": self.timestamp},
                },
            )
            logger.debug(
                "State: %s, Created: %s, State ID: %s",
                state,
                created,
                state_obj.id,
            )
            for district, local_bodies in districts.items():
                metadata = {
                    "country": self.country,
                    "govt_org_type": "district",
                    "govt_org_children_type": "local_body",
                }
                district_obj, created = Organization.objects.filter(
                    name__iexact=district,
                    parent=state_obj,
                    org_type="govt",
                    metadata=metadata,
                ).get_or_create(
                    defaults={
                        "name": district,
                        "root_org": state_obj,
                        "parent": state_obj,
                        "org_type": "govt",
                        "system_generated": True,
                        "metadata": metadata,
                        "meta": {"migration_id": self.timestamp},
                    },
                )
                logger.debug(
                    "District: %s, Created: %s, District ID: %s",
                    district,
                    created,
                    district_obj.id,
                )
                for local_body, local_body_types in local_bodies.items():
                    for local_body_type, children in local_body_types.items():
                        # children can be either ward or grama_panchayat
                        lg_type = local_body_type.replace("_", " ").title()
                        lb_name = f"{local_body} {lg_type}"
                        metadata = {
                            "country": self.country,
                            "govt_org_type": local_body_type,
                        }
                        if local_body_type == "block_panchayat":
                            metadata["govt_org_children_type"] = "grama_panchayat"
                        else:
                            metadata["govt_org_children_type"] = "ward"

                        local_body_obj, created = Organization.objects.filter(
                            name__iexact=lb_name,
                            parent=district_obj,
                            org_type="govt",
                            metadata=metadata,
                        ).get_or_create(
                            defaults={
                                "name": lb_name,
                                "root_org": state_obj,
                                "parent": district_obj,
                                "org_type": "govt",
                                "system_generated": True,
                                "metadata": metadata,
                                "meta": {"migration_id": self.timestamp},
                            },
                        )
                        logger.debug(
                            "Local Body: %s, Created: %s, Local Body ID: %s",
                            local_body,
                            created,
                            local_body_obj.id,
                        )
                        if local_body_type == "block_panchayat":
                            for grama_panchayat, wards in children.items():
                                metadata = {
                                    "country": self.country,
                                    "govt_org_type": "grama_panchayat",
                                    "govt_org_children_type": "ward",
                                }
                                gp_name = f"{grama_panchayat} Grama Panchayat"
                                grama_panchayat_obj, created = (
                                    Organization.objects.filter(
                                        name__iexact=gp_name,
                                        parent=local_body_obj,
                                        org_type="govt",
                                        metadata=metadata,
                                    ).get_or_create(
                                        defaults={
                                            "name": gp_name,
                                            "root_org": state_obj,
                                            "parent": local_body_obj,
                                            "org_type": "govt",
                                            "system_generated": True,
                                            "metadata": metadata,
                                            "meta": {"migration_id": self.timestamp},
                                        },
                                    )
                                )
                                logger.debug(
                                    "Block Panchayat: %s, Created: %s, Block Panchayat ID: %s",
                                    gp_name,
                                    created,
                                    grama_panchayat_obj.id,
                                )
                                for ward_number, ward_name in wards.items():
                                    self.create_ward(
                                        state_obj,
                                        grama_panchayat_obj,
                                        ward_number,
                                        ward_name,
                                    )
                        else:
                            for ward_number, ward_name in children.items():
                                self.create_ward(
                                    state_obj, local_body_obj, ward_number, ward_name
                                )
        logger.info("Organizations Created")
        ward_count = Organization.objects.filter(
            org_type="govt", metadata__govt_org_type="ward"
        ).count()
        logger.info("Total Wards: %s", ward_count)

    def handle(self, *args, **options):
        start_time = datetime.now(tz=UTC)
        if options["verbosity"] == 0:
            logger.setLevel(logging.ERROR)
        elif options["verbosity"] == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        self.timestamp = int(start_time.timestamp() * 1000)
        self.country = "India"

        csv_file_url = options["csv_file_url"]
        data = self.rows_to_dict(self.read_csv(csv_file_url))

        with transaction.atomic():
            self.create_organization(data)

        self.stdout.write(self.style.SUCCESS(f"migration_id: {self.timestamp}"))
        self.stdout.write(
            self.style.SUCCESS(f"Time taken: {datetime.now(tz=UTC) - start_time}")
        )
        self.stdout.write(self.style.SUCCESS("Successfully loaded Govt Organizations."))
