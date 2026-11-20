from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import (
    ValueSetCompose,
    ValueSetConcept,
    ValueSetInclude,
)
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_PROCEDURE_CODE_VALUESET = CareValueset(
    "Procedure", "system-procedure-code", ValueSetStatusOptions.active.value
)

CARE_PROCEDURE_CODE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "71388002"}],
            )
        ]
    )
)

CARE_PROCEDURE_CODE_VALUESET.register_as_system()

CARE_PROCEDURE_CATEGORY_VALUESET = CareValueset(
    "Procedure Category",
    "system-procedure-category",
    ValueSetStatusOptions.active.value,
)

# https://hl7.org/fhir/valueset-procedure-category.html
CARE_PROCEDURE_CATEGORY_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                concept=[
                    ValueSetConcept(
                        code="24642003", display="Psychiatry procedure or service"
                    ),
                    ValueSetConcept(code="409063005", display="Counseling"),
                    ValueSetConcept(code="409073007", display="Education"),
                    ValueSetConcept(
                        code="387713003", display="Surgical procedure (procedure)"
                    ),
                    ValueSetConcept(code="103693007", display="Diagnostic procedure"),
                    ValueSetConcept(
                        code="46947000", display="Chiropractic manipulation"
                    ),
                    ValueSetConcept(
                        code="410606002", display="Social service procedure (procedure)"
                    ),
                ],
            )
        ]
    )
)

CARE_PROCEDURE_CATEGORY_VALUESET.register_as_system()

CARE_PROCEDURE_REASON_VALUESET = CareValueset(
    "Procedure Reason",
    "system-procedure-reason",
    ValueSetStatusOptions.active.value,
)

# https://hl7.org/fhir/valueset-procedure-reason.html
CARE_PROCEDURE_REASON_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "404684003"}],
            ),
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": "71388002"}],
            ),
        ]
    )
)

CARE_PROCEDURE_REASON_VALUESET.register_as_system()

CARE_PROCEDURE_STATUS_REASON_VALUESET = CareValueset(
    "Procedure Status Reason",
    "system-procedure-status-reason",
    ValueSetStatusOptions.active.value,
)

# https://hl7.org/fhir/valueset-procedure-not-performed-reason.html
CARE_PROCEDURE_STATUS_REASON_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            ValueSetInclude(
                system="http://snomed.info/sct",
                filter=[{"property": "concept", "op": "is-a", "value": code}],
            )
            for code in (
                "183932001",
                "416406003",
                "416237000",
                "428119001",
                "416064006",
                "416432009",
                "183944003",
                "394908001",
            )
        ]
        + [
            ValueSetInclude(
                system="http://snomed.info/sct",
                concept=[ValueSetConcept(code="410536001", display="Contraindicated")],
            )
        ]
    )
)

CARE_PROCEDURE_STATUS_REASON_VALUESET.register_as_system()
