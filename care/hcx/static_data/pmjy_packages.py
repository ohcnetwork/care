import json
from typing import TypedDict

from redis_om import Field, Migrator

from care.utils.static_data.models.base import BaseRedisModel


class PMJYPackageObject(TypedDict):
    code: str
    name: str
    price: str
    package_name: str


class PMJYPackage(BaseRedisModel):
    code: str = Field(primary_key=True)
    name: str
    price: str
    package_name: str
    vec: str = Field(index=True, full_text_search=True)

    def get_representation(self) -> PMJYPackageObject:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "package_name": self.package_name,
        }


def load_pmjy_packages():
    print("Loading PMJY Packages into the redis cache...", end="", flush=True)
    with open("data/pmjy_packages.json", "r") as f:
        pmjy_packages = json.load(f)
        for package in pmjy_packages:
            PMJYPackage(
                code=package["procedure_code"],
                name=package["procedure_label"],
                price=package["procedure_price"],
                package_name=package["package_name"],
                vec=f"{package['procedure_label']} {package['package_name']}",
            ).save()

    Migrator().run()
    print("Done")
