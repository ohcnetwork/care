import json

from littletable import Table


def fetch_data():
    with open('data/icd11.json', 'r') as json_file:
        return json.load(json_file)


ICDDiseases = Table("ICD11")
icd11_objects = fetch_data()

IGNORE_FIELDS = ["isLeaf", "classKind", "isAdoptedChild", "averageDepth", "breadthValue", "Suggested"]

for icd11_object in icd11_objects:
    for field in IGNORE_FIELDS:
        icd11_object.pop(field, "")
    ICDDiseases.insert(icd11_object)
