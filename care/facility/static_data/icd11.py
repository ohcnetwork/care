import contextlib

from django.db import connection
from littletable import Table

from care.facility.models.icd11_diagnosis import ICD11Diagnosis


def fetch_from_db():
    # This is a hack to prevent the migration from failing when the table does not exist
    all_tables = connection.introspection.table_names()
    if "facility_icd11diagnosis" in all_tables:
        return [
            {
                "id": str(diagnosis["id"]),
                "label": diagnosis["label"],
                "is_leaf": diagnosis["is_leaf"],
            }
            for diagnosis in ICD11Diagnosis.objects.filter().values(
                "id", "label", "is_leaf"
            )
        ]
    return []


ICDDiseases = Table("ICD11")
ICDDiseases.insert_many(fetch_from_db())
ICDDiseases.create_search_index("label")
ICDDiseases.create_index("id", unique=True)


def get_icd11_diagnoses_objects_by_ids(diagnoses_ids):
    diagnosis_objects = []
    for diagnosis in diagnoses_ids:
        with contextlib.suppress(BaseException):
            diagnosis_object = ICDDiseases.by.id[diagnosis].__dict__
            diagnosis_objects.append(diagnosis_object)
    return diagnosis_objects
