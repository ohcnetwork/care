from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_ROUTE_VALUESET = CareValueset(
    "Route", "system-route", ValueSetStatusOptions.active.value
)

CARE_ROUTE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "284009009"}],
            ),
        ]
    )
)

CARE_ROUTE_VALUESET.register_as_system()
