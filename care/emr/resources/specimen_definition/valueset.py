from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose, ValueSetInclude
from care.emr.resources.valueset.spec import ValueSetStatusOptions

SPECIMEN_TYPE_CODE_VALUESET = CareValueset(
    "Specimen Type Code",
    "system-specimen_type-code",
    ValueSetStatusOptions.active.value,
)

SPECIMEN_TYPE_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/v2-0487",
                version="2.0.0",
            )
        ]
    )
)

SPECIMEN_TYPE_CODE_VALUESET.register_as_system()


PREPARE_PATIENT_PRIOR_SPECIMEN_CODE_VALUESET = CareValueset(
    "Prepare Patient Prior Specimen Code",
    "system-prepare_patient_prior_specimen_code",
    ValueSetStatusOptions.active.value,
)

PREPARE_PATIENT_PRIOR_SPECIMEN_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[
                    {
                        "property": "concept",
                        "op": "is-a",
                        "value": "703763000",
                    }
                ],
            )
        ]
    )
)

PREPARE_PATIENT_PRIOR_SPECIMEN_CODE_VALUESET.register_as_system()


SPECIMEN_COLLECTION_CODE_VALUESET = CareValueset(
    "Specimen Collection Code",
    "system-specimen_collection_code",
    ValueSetStatusOptions.active.value,
)

SPECIMEN_COLLECTION_CODE_VALUESET.register_valueset(
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
                    {"code": "278450005", "display": "Finger-prick sampling"},
                ],
            )
        ]
    )
)

SPECIMEN_COLLECTION_CODE_VALUESET.register_as_system()


CONTAINER_CAP_VALUESET = CareValueset(
    "Container Cap",
    "system-container_cap-code",
    ValueSetStatusOptions.active.value,
)

CONTAINER_CAP_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://terminology.hl7.org/CodeSystem/container-cap"
            )
        ]
    )
)

CONTAINER_CAP_VALUESET.register_as_system()
