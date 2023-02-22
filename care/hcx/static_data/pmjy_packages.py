import json

from littletable import Table


def fetch_data():
    with open("data/pmjy_packages.json", "r") as json_file:
        return json.load(json_file)


PMJYPackages = Table("ICD11")
pmjy_packages = fetch_data()

IGNORE_FIELDS = [
    "hbp_code",
    "specialty",
    "package_code",
    "package_name",
    "stratification",
    "implant",
]

for pmjy_package in pmjy_packages:
    for field in IGNORE_FIELDS:
        pmjy_package.pop(field, "")

    pmjy_package["code"] = pmjy_package.pop("procedure_code")
    pmjy_package["name"] = pmjy_package.pop("procedure_name")
    pmjy_package["price"] = pmjy_package.pop("procedure_price")
    PMJYPackages.insert(pmjy_package)

PMJYPackages.create_search_index("name")
PMJYPackages.create_index("code", unique=True)
