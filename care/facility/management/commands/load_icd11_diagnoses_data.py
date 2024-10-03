import json
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management import BaseCommand, CommandError

from care.facility.models.icd11_diagnosis import ICD11Diagnosis

if TYPE_CHECKING:
    from pathlib import Path


def fetch_data():
    icd11_json: Path = settings.BASE_DIR / "data" / "icd11.json"
    with icd11_json.open() as json_file:
        return json.load(json_file)


ICD11_ID_SUFFIX_TO_INT = {
    "mms": 1,
    "other": 2,
    "unspecified": 3,
}


def icd11_id_to_int(icd11_id):
    """
    Maps ICD11 ID to an integer.

    Eg:
    - http://id.who.int/icd/entity/594985340 -> 594985340
    - http://id.who.int/icd/entity/594985340/mms -> 5949853400001
    - http://id.who.int/icd/entity/594985340/mms/unspecified -> 5949853400003
    """
    entity_id = icd11_id.replace("http://id.who.int/icd/entity/", "")
    if entity_id.isnumeric():
        return int(entity_id)
    segments = entity_id.split("/")
    return int(segments[0]) * 1e3 + ICD11_ID_SUFFIX_TO_INT[segments[-1]]


class Command(BaseCommand):
    """
    Management command to load ICD11 diagnoses to database. Not for production
    use.
    Usage: python manage.py load_icd11_diagnoses_data
    """

    help = "Loads ICD11 diagnoses data to database"

    data = []
    roots_lookup = {}
    """
    Eg:
    ```
    {
        "http://id.who.int/icd/entity/594985340": {
            "chapter": "Certain infectious or parasitic diseases",
            "block": "Intestinal infectious diseases",
            "category": None,
        },
    }
    ```
    """

    CLASS_KIND_DB_KEYS = {
        "chapter": "meta_chapter",
        "block": "meta_root_block",
        "category": "meta_root_category",
    }

    ICD11_GROUP_LABEL_PRETTY = {
        "01 Certain infectious or parasitic diseases": "Infection and parasites ",
        "02 Neoplasms": "Neoplasms",
        "03 Diseases of the blood or blood-forming organs": "Hematology",
        "04 Diseases of the immune system": "Immune System",
        "05 Endocrine, nutritional or metabolic diseases": "Endocrine, nutritional or metabolism",
        "06 Mental, behavioural or neurodevelopmental disorders": "Mental, behavioural or neurological",
        "07 Sleep-wake disorders": "Sleep",
        "08 Diseases of the nervous system": "Nervous System",
        "09 Diseases of the visual system": "Ophthalmology",
        "10 Diseases of the ear or mastoid process": "ENT",
        "11 Diseases of the circulatory system": "Circulatory System",
        "12 Diseases of the respiratory system": "Respiratory System",
        "13 Diseases of the digestive system": "Digestive System",
        "14 Diseases of the skin": "Skin",
        "15 Diseases of the musculoskeletal system or connective tissue": "Musculoskeletal System",
        "16 Diseases of the genitourinary system": "Genitourinary System",
        "17 Conditions related to sexual health": "Sexual Health",
        "18 Pregnancy, childbirth or the puerperium": "OBGYN",
        "19 Certain conditions originating in the perinatal period": "Neonatology",
        "20 Developmental anomalies": "Developmental Anomalies",
        "21 Symptoms, signs or clinical findings, not elsewhere classified": "Others",
        "22 Injury, poisoning or certain other consequences of external causes": "Injury, Poisoning",
        "23 External causes of morbidity or mortality": "External Causes of Injury",
        "24 Factors influencing health status or contact with health services": "Reason for contact with Health Services",
        "25 Codes for special purposes": "Codes for special purposes",
        "26 Supplementary Chapter Traditional Medicine Conditions - Module I": "Supplementary chapter",
        "V Supplementary section for functioning assessment": "Functioning assessment",
    }

    def find_roots(self, item):
        id = item["ID"]

        if id in self.roots_lookup:
            return self.roots_lookup[id]

        if not item["parentId"]:
            self.roots_lookup[id] = {item["classKind"]: item["label"]}
            return self.roots_lookup[id]

        if parent := self.roots_lookup.get(item["parentId"]):

            def my(x):
                return item["label"] if item["classKind"] == x else None

            self.roots_lookup[id] = {
                "chapter": parent.get("chapter") or my("chapter"),
                "block": parent.get("block") or my("block"),
                "category": parent.get("category") or my("category"),
            }
            return self.roots_lookup[id]

        # The following code is never executed as the `icd11.json` file is
        # pre-sorted and hence the parent is always present before the child.
        self.stdout.write("Full-scan for", id, item["label"])
        return self.find_roots(
            next(
                icd11_object
                for icd11_object in self.data
                if icd11_object["ID"] == item["parentId"]
            )
        )

    def handle(self, *args, **options):
        self.stdout.write("Loading ICD11 diagnoses data to database...")
        try:
            self.data = fetch_data()

            def roots(item):
                roots = self.find_roots(item)
                mapped = self.ICD11_GROUP_LABEL_PRETTY.get(
                    roots["chapter"], roots["chapter"]
                )
                result = {
                    self.CLASS_KIND_DB_KEYS.get(k, k): v for k, v in roots.items()
                }
                result["meta_chapter_short"] = mapped
                result["meta_hidden"] = mapped is None
                return result

            ICD11Diagnosis.objects.bulk_create(
                [
                    ICD11Diagnosis(
                        id=icd11_id_to_int(obj["ID"]),
                        icd11_id=obj["ID"],
                        label=obj["label"],
                        class_kind=obj["classKind"],
                        is_leaf=obj["isLeaf"],
                        parent_id=obj["parentId"] and icd11_id_to_int(obj["parentId"]),
                        average_depth=obj["averageDepth"],
                        is_adopted_child=obj["isAdoptedChild"],
                        breadth_value=obj["breadthValue"],
                        **roots(obj),
                    )
                    for obj in self.data
                ],
                ignore_conflicts=True,  # Voluntarily set to skip duplicates, so that we can run this command multiple times + existing relations are not affected
            )
        except Exception as e:
            raise CommandError(e) from e
