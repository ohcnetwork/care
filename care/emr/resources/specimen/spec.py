import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, field_validator, model_serializer

from care.emr.models.specimen import Specimen
from care.emr.resources.base import EMRResource, model_from_cache
from care.emr.resources.common import Coding
from care.emr.resources.observation.valueset import CARE_BODY_SITE_VALUESET
from care.emr.resources.specimen.valueset import (
    COLLECTION_METHOD_VALUESET,
    FASTING_STATUS_VALUESET,
    SPECIMEN_CONDITION_VALUESET,
    SPECIMEN_PROCESSING_METHOD_VALUESET,
)
from care.emr.resources.specimen_definition.spec import SpecimenDefinitionReadSpec
from care.emr.resources.specimen_definition.valueset import SPECIMEN_TYPE_CODE_VALUESET
from care.emr.resources.user.spec import UserSpec
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding
from care.users.models import User


class SpecimenStatusOptions(str, Enum):
    """Status options for specimen"""

    draft = "draft"  # Not from FHIR
    available = "available"
    unavailable = "unavailable"
    unsatisfactory = "unsatisfactory"
    entered_in_error = "entered_in_error"


class QuantitySpec(BaseModel):
    """Represents a quantity with value and unit"""

    value: float
    unit: Coding


class DurationSpec(BaseModel):
    """Duration specification using value and unit"""

    # Needs to be moved into the common specs, with datetime based valueset check
    value: int
    unit: Coding


class CollectionSpec(BaseModel):
    """Specimen collection details"""

    collector: UUID4 | None = None
    collected_date_time: datetime.datetime | None = None  # Check for TZ
    quantity: QuantitySpec | None = None
    method: ValueSetBoundCoding[COLLECTION_METHOD_VALUESET.slug] | None = None
    procedure: UUID4 | None = None
    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    fasting_status_codeable_concept: (
        ValueSetBoundCoding[FASTING_STATUS_VALUESET.slug] | None
    ) = None
    fasting_status_duration: DurationSpec | None = None

    @field_validator("collector")
    @classmethod
    def validate_collector(cls, collector):
        if collector and not User.objects.filter(external_id=collector).exists():
            raise ValueError("Collector user not found")
        return collector

    @model_serializer
    def serialize_model(self):
        data = dict(self)
        if data.get("collector"):
            data["collector_object"] = model_from_cache(
                UserSpec, external_id=data["collector"]
            )
        return data


class ProcessingSpec(BaseModel):
    """Specimen processing details"""

    description: str
    method: ValueSetBoundCoding[SPECIMEN_PROCESSING_METHOD_VALUESET.slug] | None = None
    performer: UUID4 | None = None
    time_date_time: str

    @field_validator("performer")
    @classmethod
    def validate_performer(cls, performer):
        if performer and not User.objects.filter(external_id=performer).exists():
            raise ValueError("Performer user not found")
        return performer

    @model_serializer
    def serialize_model(self):
        data = dict(self)
        if data.get("performer"):
            data["performer_object"] = model_from_cache(
                UserSpec, external_id=data["performer"]
            )
        return data


class BaseSpecimenSpec(EMRResource):
    """Base model for specimen"""

    __model__ = Specimen
    __exclude__ = ["facility", "request"]

    id: UUID4 | None = None
    accession_identifier: str = ""
    status: SpecimenStatusOptions
    specimen_type: ValueSetBoundCoding[SPECIMEN_TYPE_CODE_VALUESET.slug]
    received_time: str | None = None
    collection: CollectionSpec | None = None
    processing: list[ProcessingSpec] = []
    condition: list[ValueSetBoundCoding[SPECIMEN_CONDITION_VALUESET.slug]] = []
    note: str | None = None


class SpecimenUpdateSpec(BaseSpecimenSpec):
    """Specimen update specification"""

    status: SpecimenStatusOptions | None = None
    specimen_type: ValueSetBoundCoding[SPECIMEN_TYPE_CODE_VALUESET.slug] | None = None


class SpecimenCreateSpec(BaseSpecimenSpec):
    """Specimen creation specification"""

    subject_patient: UUID4
    subject_encounter: UUID4
    request: UUID4 | None = None


class SpecimenReadSpec(BaseSpecimenSpec):
    """Specimen read specification"""

    specimen_definition: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        if obj.specimen_definition:
            mapping["specimen_definition"] = SpecimenDefinitionReadSpec.serialize(
                obj.specimen_definition
            ).to_json()


class SpecimenRetrieveSpec(SpecimenReadSpec):
    """Specimen retrieve specification"""

    service_request: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        from care.emr.resources.service_request.spec import ServiceRequestReadSpec

        if obj.service_request:
            mapping["service_request"] = ServiceRequestReadSpec.serialize(
                obj.service_request
            ).to_json()
