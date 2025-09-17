from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_SUBSTANCE_VALUSET = CareValueset(
    "Substance", "system-substance", ValueSetStatusOptions.active.value
)


CARE_SUBSTANCE_VALUSET.register_valueset(
    ValueSetCompose(
        include=[
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "105590001"}],
            }
        ]
    )
)

CARE_SUBSTANCE_VALUSET.register_as_system()

CARE_NUTRIENTS_VALUESET = CareValueset(
    "Nutrients", "system-nutrients", ValueSetStatusOptions.active.value
)

CARE_NUTRIENTS_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "226355009"}],
            }
        ]
    )
)

CARE_NUTRIENTS_VALUESET.register_as_system()

MEDICATION_FORM_CODES = CareValueset(
    "Medication Form Codes",
    "system-medication-form-codes",
    ValueSetStatusOptions.active.value,
)

MEDICATION_FORM_CODES.register_valueset(
    ValueSetCompose(
        include=[
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "736542009"}],
            }
        ]
    )
)

MEDICATION_FORM_CODES.register_as_system()
