from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_CODITION_CODE_VALUESET = CareValueset(
    "Condition", "system-condition-code", ValueSetStatusOptions.active.value
)

CARE_CODITION_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "404684003"}],
            )
        ]
    )
)

CARE_CODITION_CODE_VALUESET.register_as_system()
