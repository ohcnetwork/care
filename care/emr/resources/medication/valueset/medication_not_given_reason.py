from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_MEDICATION_NOT_GIVEN_REASON_VALUESET = CareValueset(
    "Medication Not Given Reason",
    "system-medication-not-given",
    ValueSetStatusOptions.active.value,
)

CARE_MEDICATION_NOT_GIVEN_REASON_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "242990004"}],
            ),
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "182895007"}],
            ),
        ]
    )
)

CARE_MEDICATION_NOT_GIVEN_REASON_VALUESET.register_as_system()
