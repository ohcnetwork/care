from care.emr.resources.base import model_from_cache
from care.emr.resources.healthcare_service.spec import HealthcareServiceReadSpec
from care.emr.resources.location.spec import FacilityLocationListSpec
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.emr.resources.user.spec import UserSpec


def serialize_resource(obj):
    if obj.resource_type == SchedulableResourceTypeOptions.practitioner.value:
        return model_from_cache(UserSpec, id=obj.user_id)
    if obj.resource_type == SchedulableResourceTypeOptions.healthcare_service.value:
        return HealthcareServiceReadSpec.serialize(obj.healthcare_service).to_json()
    if obj.resource_type == SchedulableResourceTypeOptions.location.value:
        return FacilityLocationListSpec.serialize(obj.location).to_json()
    return {}
