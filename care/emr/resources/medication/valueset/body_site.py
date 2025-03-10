from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_BODY_SITE_VALUESET = CareValueset(
    "Body Site", "system-body-site", ValueSetStatusOptions.active.value
)

CARE_BODY_SITE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "91723000"}],
            ),
        ]
    )
)

CARE_BODY_SITE_VALUESET.register_as_system()
