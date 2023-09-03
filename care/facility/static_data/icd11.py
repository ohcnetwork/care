import contextlib
import json

from littletable import Table


def fetch_data():
    with open("data/icd11.json") as json_file:
        return json.load(json_file)


def is_numeric(val):
    if str(val).isnumeric():
        return val
    return -1


ICDDiseases = Table("ICD11")
icd11_objects = fetch_data()
entity_id = ""
IGNORE_FIELDS = [
    "isLeaf",
    "classKind",
    "isAdoptedChild",
    "averageDepth",
    "breadthValue",
    "Suggested",
]

for icd11_object in icd11_objects:
    for field in IGNORE_FIELDS:
        icd11_object.pop(field, "")
    icd11_object["id"] = icd11_object.pop("ID")
    entity_id = icd11_object["id"].split("/")[-1]
    icd11_object["id"] = is_numeric(entity_id)
    if icd11_object["id"] == -1:
        continue
    if icd11_object["id"]:
        ICDDiseases.insert(icd11_object)

ICDDiseases.create_search_index("label")
ICDDiseases.create_index("id", unique=True)


def get_icd11_diagnoses_objects_by_ids(diagnoses_ids):
    diagnosis_objects = []
    for diagnosis in diagnoses_ids:
        with contextlib.suppress(BaseException):
            diagnosis_object = ICDDiseases.by.id[diagnosis].__dict__
            diagnosis_objects.append(diagnosis_object)
    return diagnosis_objects
