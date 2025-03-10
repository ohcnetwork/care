from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_ADMINISTRATION_METHOD_VALUESET = CareValueset(
    "Administration Method",
    "system-administration-method",
    ValueSetStatusOptions.active.value,
)

CARE_ADMINISTRATION_METHOD_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "736665006"}],
            ),
        ]
    )
)

CARE_ADMINISTRATION_METHOD_VALUESET.register_as_system()
