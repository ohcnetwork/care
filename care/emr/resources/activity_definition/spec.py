from enum import Enum

from pydantic import UUID4

from care.emr.models import ActivityDefinition
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.models.observation_definition import ObservationDefinition
from care.emr.models.specimen_definition import SpecimenDefinition
from care.emr.resources.activity_definition.valueset import (
    ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET,
)
from care.emr.resources.base import EMRResource
from care.emr.resources.charge_item_definition.spec import ChargeItemDefinitionReadSpec
from care.emr.resources.healthcare_service.spec import HealthcareServiceReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.observation.valueset import (
    CARE_BODY_SITE_VALUESET,
    CARE_OBSERVATION_VALUSET,
)
from care.emr.resources.observation_definition.spec import ObservationDefinitionReadSpec
from care.emr.resources.specimen_definition.spec import SpecimenDefinitionReadSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class ActivityDefinitionStatusOptions(str, Enum):
    """Status options for activity definition"""

    draft = "draft"
    active = "active"
    retired = "retired"
    unknown = "unknown"


class ActivityDefinitionKindOptions(str, Enum):
    service_request = "service_request"


class ActivityDefinitionCategoryOptions(str, Enum):
    laboratory = "laboratory"
    imaging = "imaging"
    counselling = "counselling"
    surgical_procedure = "surgical_procedure"


class BaseActivityDefinitionSpec(EMRResource):
    """Base model for activity definition"""

    __model__ = ActivityDefinition
    __exclude__ = ["facility"]

    id: UUID4 | None = None
    slug: str
    title: str
    derived_from_uri: str | None = None
    status: ActivityDefinitionStatusOptions
    description: str = ""
    usage: str = ""
    category: ActivityDefinitionCategoryOptions
    kind: ActivityDefinitionKindOptions
    code: ValueSetBoundCoding[ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET.slug]
    body_site: ValueSetBoundCoding[CARE_BODY_SITE_VALUESET.slug] | None = None
    diagnostic_report_codes: list[
        ValueSetBoundCoding[CARE_OBSERVATION_VALUSET.slug]
    ] = []


class ActivityDefinitionWriteSpec(BaseActivityDefinitionSpec):
    locations: list[UUID4] = []
    specimen_requirements: list[UUID4]
    observation_result_requirements: list[UUID4]
    healthcare_service: UUID4 | None = None
    charge_item_definitions: list[UUID4] = []

    def perform_extra_deserialization(self, is_update, obj):
        if self.healthcare_service:
            obj.healthcare_service = HealthcareService.objects.only("id").get(
                external_id=self.healthcare_service
            )


class ActivityDefinitionReadSpec(BaseActivityDefinitionSpec):
    """Activity definition read specification"""

    version: int | None = None
    tags: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["tags"] = SingleFacilityTagManager().render_tags(obj)


class ActivityDefinitionRetrieveSpec(ActivityDefinitionReadSpec):
    """Activity definition retrieve specification"""

    specimen_requirements: list[dict]
    observation_result_requirements: list[dict]
    locations: list[dict]
    healthcare_service: dict | None = None
    charge_item_definitions: list[dict]

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        specimen_requirements = []
        for specimen_requirement in obj.specimen_requirements:
            specimen_requirements.append(
                SpecimenDefinitionReadSpec.serialize(
                    SpecimenDefinition.objects.get(id=specimen_requirement)
                ).to_json()
            )
        mapping["specimen_requirements"] = specimen_requirements
        observation_result_requirements = []
        for observation_result_requirement in obj.observation_result_requirements:
            observation_result_requirements.append(
                ObservationDefinitionReadSpec.serialize(
                    ObservationDefinition.objects.get(id=observation_result_requirement)
                ).to_json()
            )
        mapping["observation_result_requirements"] = observation_result_requirements
        locations = []
        for location in obj.locations:
            try:
                locations.append(
                    FacilityLocationListSpec.serialize(
                        FacilityLocation.objects.get(id=location)
                    ).to_json()
                )
            except Exception:  # noqa S110
                pass
        mapping["locations"] = locations
        if obj.healthcare_service:
            mapping["healthcare_service"] = HealthcareServiceReadSpec.serialize(
                obj.healthcare_service
            ).to_json()
        charge_item_definitions = []
        for charge_item_definition in obj.charge_item_definitions:
            charge_item_definitions.append(
                ChargeItemDefinitionReadSpec.serialize(
                    ChargeItemDefinition.objects.get(id=charge_item_definition)
                ).to_json()
            )
        mapping["charge_item_definitions"] = charge_item_definitions
