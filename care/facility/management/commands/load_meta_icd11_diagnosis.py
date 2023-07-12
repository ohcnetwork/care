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
                "chapter": parent.get("chapter", my("chapter")),
                "block": parent.get("block", my("block")),
                "category": parent.get("category", my("category")),
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
                return {
                    self.CLASS_KIND_DB_KEYS.get(k, k): v
                    for k, v in self.find_roots(item).items()
                }

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
