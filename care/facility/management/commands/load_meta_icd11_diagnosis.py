from django.core.management import BaseCommand, CommandError

from care.facility.models.meta_icd11_diagnosis import MetaICD11Diagnosis
from care.facility.static_data.icd11 import fetch_data


class Command(BaseCommand):
    """
    Management command to load ICD11 diagnoses to database. Not for production
    use.
    Usage: python manage.py load_meta_icd11_diagnosis
    """

    help = "Loads ICD11 data to a table in to database."

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
        "block": "root_block",
        "category": "root_category",
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
        "22 Injury, poisoning or certain other consequences of external causes": "Injury, Poisoning ",
        "23 External causes of morbidity or mortality": "External Causes of Injury",
        "24 Factors influencing health status or contact with health services": None,
        "25 Codes for special purposes": "Codes for special purposes",
        "26 Supplementary Chapter Traditional Medicine Conditions - Module I": None,
        "V Supplementary section for functioning assessment": "Functioning assessment ",
        "X Extension Codes": "NOT RELEVANT",
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
        print("Full-scan for", id, item["label"])
        return self.find_roots(
            [
                icd11_object
                for icd11_object in self.data
                if icd11_object["ID"] == item["parentId"]
            ][0]
        )

    def handle(self, *args, **options):
        print("Loading ICD11 data to DB Table (meta_icd11_diagnosis)...")
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
                result["chapter_short"] = mapped
                result["deleted"] = mapped is None
                return result

            MetaICD11Diagnosis.objects.all().delete()
            MetaICD11Diagnosis.objects.bulk_create(
                [
                    MetaICD11Diagnosis(
                        id=icd11_object["ID"],
                        _id=int(icd11_object["ID"].split("/")[-1]),
                        average_depth=icd11_object["averageDepth"],
                        is_adopted_child=icd11_object["isAdoptedChild"],
                        parent_id=icd11_object["parentId"],
                        class_kind=icd11_object["classKind"],
                        is_leaf=icd11_object["isLeaf"],
                        label=icd11_object["label"],
                        breadth_value=icd11_object["breadthValue"],
                        **roots(icd11_object),
                    )
                    for icd11_object in self.data
                    if icd11_object["ID"].split("/")[-1].isnumeric()
                ]
            )
            print("Done loading ICD11 data to database.")
        except Exception as e:
            raise CommandError(e)
