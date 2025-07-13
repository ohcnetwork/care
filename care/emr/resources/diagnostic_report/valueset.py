from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

DIAGNOSTIC_SERVICE_SECTIONS_CODE_VALUESET = CareValueset(
    "Diagnostic Service Sections",
    "system-diagnostic-service-sections-code",
    ValueSetStatusOptions.active.value,
)

DIAGNOSTIC_SERVICE_SECTIONS_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/v2-0074",
            )
        ]
    )
)

DIAGNOSTIC_SERVICE_SECTIONS_CODE_VALUESET.register_as_system()
