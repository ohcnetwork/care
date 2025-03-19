from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_AS_NEEDED_REASON_VALUESET = CareValueset(
    "As Needed", "system-as-needed-reason", ValueSetStatusOptions.active.value
)

CARE_AS_NEEDED_REASON_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "404684003"}],
            ),
        ]
    )
)

CARE_AS_NEEDED_REASON_VALUESET.register_as_system()
