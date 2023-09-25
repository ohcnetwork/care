import contextlib
import json

from littletable import Table

from care.facility.models.icd11_diagnosis import ICD11Diagnosis


def fetch_data():
    with open("data/icd11.json", "r") as json_file:
        return json.load(json_file)


def fetch_from_db():
    return ICD11Diagnosis.objects.all().values("id", "label")


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
