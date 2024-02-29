from django.core.management import BaseCommand, CommandError

from care.facility.models.icd11_diagnosis import ICD11Diagnosis
from care.facility.utils.icd.common_data import fetch_icd11_data, icd11_id_to_int, roots


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

    def handle(self, *args, **options):
        print("Loading ICD11 diagnoses data to database...")
        try:
            self.data = fetch_icd11_data()
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
                        **roots(obj, self.roots_lookup),
                    )
                    for obj in self.data
                ],
                ignore_conflicts=True,  # Voluntarily set to skip duplicates, so that we can run this command multiple times + existing relations are not affected
            )
        except Exception as e:
            raise CommandError(e)
