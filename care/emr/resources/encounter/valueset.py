from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

PRACTITIONER_ROLE_VALUESET = CareValueset(
    "Practitioner Role",
    "system-practitioner-role-code",
    ValueSetStatusOptions.active.value,
)

PRACTITIONER_ROLE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "223366009"}],
            ),
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "224930009"}],
            ),
        ]
    )
)

PRACTITIONER_ROLE_VALUESET.register_as_system()
