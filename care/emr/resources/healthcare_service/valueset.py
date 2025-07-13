from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

HEALTHCARE_SERVICE_TYPE_CODE_VALUESET = CareValueset(
    "Healthcare Service Type Code",
    "healthcare-service-type-code",
    ValueSetStatusOptions.active.value,
)

HEALTHCARE_SERVICE_TYPE_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/service-type",
                version="2.0.0",
            )
        ]
    )
)

HEALTHCARE_SERVICE_TYPE_CODE_VALUESET.register_as_system()
