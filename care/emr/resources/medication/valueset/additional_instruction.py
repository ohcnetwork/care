from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_ADDITIONAL_INSTRUCTION_VALUESET = CareValueset(
    "Additional Instruction",
    "system-additional-instruction",
    ValueSetStatusOptions.active.value,
)

CARE_ADDITIONAL_INSTRUCTION_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "419492006"}],
            ),
        ]
    )
)

CARE_ADDITIONAL_INSTRUCTION_VALUESET.register_as_system()
