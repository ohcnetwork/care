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

    def handle(self, *args, **options):
        print("Loading ICD11 data to database...")
        try:
            icd11_objects = fetch_data()
            MetaICD11Diagnosis.objects.all().delete()
            MetaICD11Diagnosis.objects.bulk_create(
                [
                    MetaICD11Diagnosis(
                        id=icd11_object["ID"],
                        _id=int(icd11_object["ID"].split("/")[5]),
                        average_depth=icd11_object["averageDepth"],
                        is_adopted_child=icd11_object["isAdoptedChild"],
                        parent_id=icd11_object["parentId"],
                        class_kind=icd11_object["classKind"],
                        is_leaf=icd11_object["isLeaf"],
                        label=icd11_object["label"],
                        breadth_value=icd11_object["breadthValue"],
                    )
                    for icd11_object in icd11_objects
                ]
            )
            print("Done loading ICD11 data to database.")
        except Exception as e:
            raise CommandError(e)
