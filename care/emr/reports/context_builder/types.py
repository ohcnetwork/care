from care.emr.reports.context_builder.type_registry import FieldTypeRegistry

FieldTypeRegistry.register(
    "DosageInstruction",
    {
        "name": "DosageInstruction",
        "description": "Medication dosage instruction with timing and route",
        "structure": {
            "dose": "string",
            "route": "string",
            "frequency": "string",
            "duration": "string",
            "site": "string",
            "method": "string",
            "as_needed": "boolean",
            "additional_instructions": "list[string]",
        },
        "example": {
            "dose": "1 tablet",
            "route": "Oral",
            "frequency": "Twice daily",
            "duration": "7 days",
            "site": "",
            "method": "",
            "as_needed": False,
            "additional_instructions": ["Take with food"],
        },
    },
)

FieldTypeRegistry.register(
    "CareTeamMember",
    {
        "name": "CareTeamMember",
        "description": "Member of the healthcare team caring for the patient",
        "structure": {
            "name": "string",
            "role": "string",
        },
        "example": {"name": "Dr. Rajesh Kumar", "role": "Primary Physician"},
    },
)

FieldTypeRegistry.register(
    "CodeableConcept",
    {
        "name": "CodeableConcept",
        "description": "FHIR CodeableConcept - coded value with display text and coding system",
        "structure": {
            "code": "string",
            "display": "string",
            "system": "string",
        },
        "example": {
            "code": "5A11",
            "display": "Type 2 Diabetes Mellitus",
            "system": "ICD-11",
        },
    },
)

FieldTypeRegistry.register(
    "Quantity",
    {
        "name": "Quantity",
        "description": "FHIR Quantity - measured amount with unit",
        "structure": {
            "value": "float",
            "unit": "string",
            "system": "string",
            "code": "string",
        },
        "example": {
            "value": 120.0,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]",
        },
    },
)
