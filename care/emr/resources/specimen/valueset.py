from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

# Collection method valueset (SNOMED)
COLLECTION_METHOD_VALUESET = CareValueset(
    "Collection Method",
    "system-collection-method-code",
    ValueSetStatusOptions.active.value,
)

COLLECTION_METHOD_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                concept=[
                    {
                        "code": "129316008",
                        "display": "Aspiration - action",
                    },
                    {"code": "129314006", "display": "Biopsy - action"},
                    {"code": "129300006", "display": "Puncture - action"},
                    {"code": "129304002", "display": "Excision - action"},
                    {"code": "129323009", "display": "Scraping - action"},
                    {
                        "code": "73416001",
                        "display": "Urine specimen collection, clean catch",
                    },
                    {"code": "225113003", "display": "Timed urine collection"},
                    {
                        "code": "70777001",
                        "display": "Urine specimen collection, catheterized",
                    },
                    {"code": "386089008", "display": "Collection of coughed sputum"},
                    {
                        "code": "278450005",
                        "display": "Finger-prick sampling",
                    },
                ],
            )
        ]
    )
)

COLLECTION_METHOD_VALUESET.register_as_system()

# Fasting status valueset
FASTING_STATUS_VALUESET = CareValueset(
    "Fasting Status",
    "system-fasting-status-code",
    ValueSetStatusOptions.active.value,
)

FASTING_STATUS_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/v2-0916",
                version="2.0.0",
            )
        ]
    )
)

FASTING_STATUS_VALUESET.register_as_system()

# Specimen condition valueset
SPECIMEN_CONDITION_VALUESET = CareValueset(
    "Specimen Condition",
    "system-specimen-condition-code",
    ValueSetStatusOptions.active.value,
)

SPECIMEN_CONDITION_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/v2-0493",
                version="2.0.0",
            )
        ]
    )
)

SPECIMEN_CONDITION_VALUESET.register_as_system()


# Specimen Processing Method valueset
SPECIMEN_PROCESSING_METHOD_VALUESET = CareValueset(
    "Specimen Processing Method",
    "system-specimen-processing-method-code",
    ValueSetStatusOptions.active.value,
)

SPECIMEN_PROCESSING_METHOD_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[
                    {
                        "property": "constraint",
                        "op": "=",
                        "value": "< 9265001",
                    }
                ],
            )
        ]
    )
)

SPECIMEN_PROCESSING_METHOD_VALUESET.register_as_system()
