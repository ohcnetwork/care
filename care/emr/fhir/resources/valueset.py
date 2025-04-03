from pydantic.main import BaseModel

from care.emr.fhir.resources.base import ResourceManger
from care.emr.fhir.resources.code_concept import MinimalCodeConcept
from care.emr.resources.common.coding import Coding
from care.emr.resources.common.valueset import ValueSetInclude


class ValueSetFilterValidation(BaseModel):
    include: list[ValueSetInclude] = None
    exclude: list[ValueSetInclude] = None
    search: str = None
    count: int = None


class ValueSetResource(ResourceManger):
    allowed_properties = ["include", "exclude", "search", "count", "display_language"]

    def serialize(self, result):
        return MinimalCodeConcept(
            system=result["system"],
            code=result["code"],
            display=result["display"],
            designation=result.get("designation", []),
        )

    def validate_filter(self):
        ValueSetFilterValidation(**self._filters)

    def lookup(self, code: Coding):
        parameters = [
            {
                "name": "valueSet",
                "resource": {
                    "resourceType": "ValueSet",
                    "compose": {
                        "include": self._filters.get("include", []),
                        "exclude": self._filters.get("exclude", []),
                    },
                },
            },
            {"name": "coding", "valueCoding": code.model_dump(exclude_defaults=True)},
        ]
        request_json = {"resourceType": "Parameters", "parameter": parameters}

        full_result = self.query("POST", "ValueSet/$validate-code", request_json)
        if "parameter" not in full_result:
            raise ValueError("Valueset does not have specified code")
        results = full_result["parameter"]
        for result in results:
            if result["name"] == "result":
                return result["valueBoolean"]
        return False

    def search(self):
        parameters = []
        if self._filters.get("search"):
            parameters.append(
                {"name": "filter", "valueString": self._filters["search"]}
            )
        if "count" in self._filters:
            parameters.append({"name": "count", "valueInteger": self._filters["count"]})
        if "display_language" in self._filters:
            parameters.append(
                {
                    "name": "displayLanguage",
                    "valueString": self._filters["display_language"],
                }
            )
        parameters.append(
            {
                "name": "valueSet",
                "resource": {
                    "resourceType": "ValueSet",
                    "compose": {
                        "include": self._filters.get("include", []),
                        "exclude": self._filters.get("exclude", []),
                    },
                },
            }
        )
        parameters.append({"name": "includeDesignations", "valueBoolean": True})
        request_json = {"resourceType": "Parameters", "parameter": parameters}
        full_result = self.query("POST", "ValueSet/$expand", request_json)
        # TODO Add Exception Handling
        if "expansion" not in full_result:
            return []
        results = full_result["expansion"]
        if "contains" not in results:
            return []
        return self.handle_list(results["contains"])
