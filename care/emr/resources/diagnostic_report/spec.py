import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.observation import Observation
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.base import EMRResource
from care.emr.resources.diagnostic_report.valueset import (
    DIAGNOSTIC_SERVICE_SECTIONS_CODE_VALUESET,
)
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.observation.spec import ObservationRetrieveSpec
from care.emr.resources.observation.valueset import CARE_OBSERVATION_VALUSET
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.utils.shortcuts import get_object_or_404


class DiagnosticReportStatusChoices(str, Enum):
    registered = "registered"
    partial = "partial"
    preliminary = "preliminary"
    # modified = "modified"
    final = "final"


class DiagnosticReportSpecBase(EMRResource):
    __model__ = DiagnosticReport
    __exclude__ = ["service_request"]

    id: UUID4 | None = None
    status: DiagnosticReportStatusChoices
    category: ValueSetBoundCoding[DIAGNOSTIC_SERVICE_SECTIONS_CODE_VALUESET.slug]
    code: ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug] | None = None
    note: str | None = None
    conclusion: str | None = None


class DiagnosticReportCreateSpec(DiagnosticReportSpecBase):
    service_request: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        obj.service_request = get_object_or_404(
            ServiceRequest, external_id=self.service_request
        )


class DiagnosticReportUpdateSpec(DiagnosticReportSpecBase):
    status: DiagnosticReportStatusChoices | None = None


class DiagnosticReportListSpec(DiagnosticReportSpecBase):
    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id


class DiagnosticReportRetrieveSpec(DiagnosticReportListSpec):
    observations: list[dict] = []
    encounter: dict

    created_by: dict | None = None
    updated_by: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        cls.serialize_audit_users(mapping, obj)

        observations = Observation.objects.filter(diagnostic_report=obj)
        mapping["observations"] = [
            ObservationRetrieveSpec.serialize(observation).to_json()
            for observation in observations
        ]
        mapping["encounter"] = EncounterListSpec.serialize(obj.encounter).to_json()
