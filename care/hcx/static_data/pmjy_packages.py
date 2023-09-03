import json

from littletable import Table


def fetch_data():
    with open("data/pmjy_packages.json") as json_file:
        return json.load(json_file)


PMJYPackages = Table("PMJYPackages")
pmjy_packages = fetch_data()

IGNORE_FIELDS = [
    "hbp_code",
    "specialty",
    "package_code",
    "stratification",
    "implant",
]

for pmjy_package in pmjy_packages:
    for field in IGNORE_FIELDS:
        pmjy_package.pop(field, "")

    pmjy_package["code"] = pmjy_package.pop("procedure_code")
    pmjy_package["name"] = pmjy_package.pop("procedure_label")
    pmjy_package["price"] = pmjy_package.pop("procedure_price")
    PMJYPackages.insert(pmjy_package)

del pmjy_packages

PMJYPackages.create_search_index("name")
PMJYPackages.create_search_index("package_name")
PMJYPackages.create_index("code", unique=True)
