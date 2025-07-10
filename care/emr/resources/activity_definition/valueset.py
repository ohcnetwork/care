from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET = CareValueset(
    "Activity Definition Procedure Code",
    "activity-definition-procedure-code",
    ValueSetStatusOptions.active.value,
)

ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "71388002"}],
            )
        ]
    )
)

ACTIVITY_DEFINITION_PROCEDURE_CODE_VALUESET.register_as_system()
