import json

from littletable import Table


def fetch_data():
    with open("data/icd11.json", "r") as json_file:
        return json.load(json_file)


def parse_int(str_val):
    try:
        return int(str_val)
    except BaseException:
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
    entity_id = icd11_object["ID"].split("/")[-1]
    icd11_object["ID"] = parse_int(entity_id)
    if icd11_object["ID"] == -1:
        continue
    if icd11_object["ID"]:
        ICDDiseases.insert(icd11_object)

ICDDiseases.create_search_index("label")
# ICDDiseases.create_index("ID", unique=True) ## Duplicates are found so indexing is not possible
