from pydantic.main import BaseModel

from care.emr.fhir.resources.base import ResourceManger
from care.emr.fhir.utils import parse_fhir_parameter_output


class CodeConceptResource(ResourceManger):
    allowed_properties = ["system", "code", "property"]
    resource = "CodeConcept"

    def serialize_lookup(self, result):
        return parse_fhir_parameter_output(result)

    def get(self):
        if "system" not in self._filters or "code" not in self._filters:
            err = "Both system and code are required"
            raise ValueError(err)
        full_result = self.query("GET", "CodeSystem/$lookup", self._filters)
        return self.serialize_lookup(full_result["parameter"])


class MinimalCodeConcept(BaseModel):
    display: str
    system: str
    code: str
    designation: list | None = None


class CodeConcept(MinimalCodeConcept):
    name: str
    property: dict
