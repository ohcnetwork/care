import datetime
from enum import Enum

from django.shortcuts import get_object_or_404
from pydantic import UUID4

from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.encounter import Encounter
from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.models.service_request import ServiceRequest
from care.emr.models.specimen import Specimen
from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
    ActivityDefinitionReadSpec,
)
from care.emr.resources.activity_definition.valueset import (
    ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.diagnostic_report.spec import DiagnosticReportListSpec
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.healthcare_service.spec import HealthcareServiceReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.observation.valueset import CARE_BODY_SITE_VALUESET
from care.emr.resources.specimen.spec import SpecimenReadSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class ServiceRequestStatusChoices(str, Enum):
    """Status values for service requests"""

    draft = "draft"
    active = "active"
    on_hold = "on_hold"
    entered_in_error = "entered_in_error"
    ended = "ended"
    completed = "completed"
    revoked = "revoked"


SERVICE_REQUEST_COMPLETED_CHOICES = [
    ServiceRequestStatusChoices.completed,
    ServiceRequestStatusChoices.revoked,
    ServiceRequestStatusChoices.ended,
    ServiceRequestStatusChoices.entered_in_error,
]


class ServiceRequestIntentChoices(str, Enum):
    """Intent values for service requests"""

    proposal = "proposal"
    plan = "plan"
    directive = "directive"
    order = "order"


class ServiceRequestPriorityChoices(str, Enum):
    """Priority values for service requests"""

    routine = "routine"
    urgent = "urgent"
    asap = "asap"
    stat = "stat"


class BaseServiceRequestSpec(EMRResource):
    """Base model for service requests"""

    __model__ = ServiceRequest
    __exclude__ = ["encounter", "healthcare_service", "locations"]

    id: str | None = None
    title: str
    status: ServiceRequestStatusChoices
    intent: ServiceRequestIntentChoices
    priority: ServiceRequestPriorityChoices
    category: ActivityDefinitionCategoryOptions
    do_not_perform: bool | None = None
    note: str | None = None
    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    code: ValueSetBoundCoding[ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET.slug]
    occurance: datetime.datetime | None = None
    patient_instruction: str | None = None


class ServiceRequestWriteSpec(BaseServiceRequestSpec):
    healthcare_service: UUID4 | None = None
    locations: list[UUID4] = []

    def perform_extra_deserialization(self, is_update, obj):
        if self.healthcare_service:
            obj.healthcare_service = HealthcareService.objects.get(
                external_id=self.healthcare_service
            )
        obj._locations = self.locations  # noqa SLF001


class ServiceRequestUpdateSpec(ServiceRequestWriteSpec):
    """Update specification for service requests"""

    title: str | None = None
    status: ServiceRequestStatusChoices | None = None
    intent: ServiceRequestIntentChoices | None = None
    priority: ServiceRequestPriorityChoices | None = None
    category: ActivityDefinitionCategoryOptions | None = None
    code: (
        ValueSetBoundCoding[ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET.slug] | None
    ) = None


class ServiceRequestCreateSpec(ServiceRequestWriteSpec):
    """Create specification for service requests"""

    encounter: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        super().perform_extra_deserialization(is_update, obj)
        obj.encounter = get_object_or_404(Encounter, external_id=self.encounter)
        obj.patient = obj.encounter.patient


class ServiceRequestReadSpec(BaseServiceRequestSpec):
    """Read specification for service requests"""

    created_date: datetime.datetime
    modified_date: datetime.datetime
    encounter: dict
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["encounter"] = EncounterListSpec.serialize(obj.encounter).to_json()
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)


class ServiceRequestRetrieveSpec(ServiceRequestReadSpec):
    """Read specification for service requests"""

    locations: list[dict]
    healthcare_service: dict | None = None

    activity_definition: dict | None = None
    specimens: list[dict] | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    diagnostic_reports: list[dict] | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        locations = []
        for location in FacilityLocation.objects.filter(id__in=obj.locations):
            locations.append(FacilityLocationListSpec.serialize(location).to_json())

        mapping["locations"] = locations
        if obj.healthcare_service:
            mapping["healthcare_service"] = HealthcareServiceReadSpec.serialize(
                obj.healthcare_service
            ).to_json()
        if obj.activity_definition:
            mapping["activity_definition"] = ActivityDefinitionReadSpec.serialize(
                obj.activity_definition
            ).to_json()
        specimens = Specimen.objects.filter(service_request=obj).select_related(
            "specimen_definition"
        )
        mapping["specimens"] = [
            SpecimenReadSpec.serialize(specimen).to_json() for specimen in specimens
        ]
        diagnostic_reports = DiagnosticReport.objects.filter(service_request=obj)
        mapping["diagnostic_reports"] = [
            DiagnosticReportListSpec.serialize(diagnostic_report).to_json()
            for diagnostic_report in diagnostic_reports
        ]

        cls.serialize_audit_users(mapping, obj)
