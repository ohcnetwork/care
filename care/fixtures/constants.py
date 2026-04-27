from care.emr.resources.healthcare_service.spec import (
    HealthcareServiceInternalType,  # noqa: F401
)
from care.emr.resources.inventory.product_knowledge.spec import (
    ProductTypeOptions,
)
from care.emr.resources.observation_definition.spec import (
    ObservationCategoryChoices,
)
from care.emr.resources.questionnaire.spec import QuestionType

# Coding constant

UCUM_ML = {
    "code": "mL",
    "system": "http://unitsofmeasure.org",
    "display": "milliliter",
}
UCUM_H = {
    "code": "h",
    "system": "http://unitsofmeasure.org",
    "display": "hours",
}
UCUM_G_DL = {
    "code": "g/dL",
    "system": "http://unitsofmeasure.org",
    "display": "gram per deciliter",
}
UCUM_D = {
    "code": "d",
    "system": "http://unitsofmeasure.org",
    "display": "days",
}
UCUM_PERCENT = {
    "code": "%",
    "system": "http://unitsofmeasure.org",
    "display": "percent",
}
UCUM_MILLION_PER_UL = {
    "code": "10*6/uL",
    "system": "http://unitsofmeasure.org",
    "display": "million per microliter",
}
UCUM_THOUSANDS_PER_UL = {
    "code": "10*3/uL",
    "system": "http://unitsofmeasure.org",
    "display": "Thousands Per MicroLiter",
}
UCUM_TABLET = {
    "code": "{tbl}",
    "system": "http://unitsofmeasure.org",
    "display": "tablets",
}
UCUM_COUNT = {
    "code": "{count}",
    "system": "http://unitsofmeasure.org",
    "display": "count",
}
UCUM_YEAR = {
    "code": "a",
    "system": "http://unitsofmeasure.org",
    "display": "year",
}

HL7_BLDV = {
    "code": "BLDV",
    "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
    "display": "Blood venous",
}
HL7_UR = {
    "code": "UR",
    "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
    "display": "Urine",
}

HL7_GREY_CAP = {
    "code": "grey",
    "system": "http://terminology.hl7.org/CodeSystem/container-cap",
    "display": "grey cap",
}
HL7_LAVENDER_CAP = {
    "code": "lavender",
    "system": "http://terminology.hl7.org/CodeSystem/container-cap",
    "display": "lavender cap",
}
HL7_YELLOW_CAP = {
    "code": "yellow",
    "system": "http://terminology.hl7.org/CodeSystem/container-cap",
    "display": "yellow cap",
}
HL7_DARK_YELLOW_CAP = {
    "code": "dark-yellow",
    "system": "http://terminology.hl7.org/CodeSystem/container-cap",
    "display": "dark yellow cap",
}

SNOMED_AFTER_FASTING = {
    "code": "726054005",
    "system": "http://snomed.info/sct",
    "display": "After fasting",
}
SNOMED_SAME_DAY_BEFORE = {
    "code": "47531000087108",
    "system": "http://snomed.info/sct",
    "display": "Same day but before procedure",
}
SNOMED_PUNCTURE = {
    "code": "129300006",
    "system": "http://snomed.info/sct",
    "display": "Puncture - action",
}
SNOMED_URINE_CLEAN_CATCH = {
    "code": "73416001",
    "system": "http://snomed.info/sct",
    "display": "Urine specimen collection, clean catch",
}
SNOMED_AUTOMATED_COUNT = {
    "code": "702659008",
    "system": "http://snomed.info/sct",
    "display": "Automated count",
}
SNOMED_URINE_DIPSTICK = {
    "code": "167226008",
    "system": "http://snomed.info/sct",
    "display": "Urine dipstick test",
}
SNOMED_CBC = {
    "code": "26604007",
    "system": "http://snomed.info/sct",
    "display": "Complete blood count",
}
SNOMED_FASTING_GLUCOSE = {
    "code": "271062006",
    "system": "http://snomed.info/sct",
    "display": "Fasting blood glucose measurement",
}
SNOMED_LIPID_PANEL = {
    "code": "16254007",
    "system": "http://snomed.info/sct",
    "display": "Lipid panel",
}
SNOMED_URINE_EVAL = {
    "code": "442564008",
    "system": "http://snomed.info/sct",
    "display": "Evaluation of urine specimen",
}
SNOMED_ORAL_TABLET = {
    "code": "421026006",
    "system": "http://snomed.info/sct",
    "display": "Oral tablet",
}
SNOMED_ORAL_ROUTE = {
    "code": "26643006",
    "system": "http://snomed.info/sct",
    "display": "Oral route",
}
SNOMED_AMOXICILLIN = {
    "code": "27658006",
    "system": "http://snomed.info/sct",
    "display": "Amoxicillin-containing product",
}
SNOMED_PARACETAMOL = {
    "code": "90332006",
    "system": "http://snomed.info/sct",
    "display": "Paracetamol-containing product",
}
SNOMED_IBUPROFEN = {
    "code": "38268001",
    "system": "http://snomed.info/sct",
    "display": "Ibuprofen-containing product",
}
SNOMED_GLOVES = {
    "code": "46713009",
    "system": "http://snomed.info/sct",
    "display": "Gloves",
}

LOINC_FASTING_GLUCOSE = {
    "code": "1558-6",
    "system": "http://loinc.org",
    "display": "Fasting glucose [Mass/volume] in Serum or Plasma",
}
LOINC_CBC_PANEL = {
    "code": "58410-2",
    "system": "http://loinc.org",
    "display": "CBC panel - Blood by Automated count",
}
LOINC_HEMOGLOBIN = {
    "code": "LP32067-8",
    "system": "http://loinc.org",
    "display": "Hemoglobin",
}
LOINC_HEMATOCRIT = {
    "code": "LP15101-6",
    "system": "http://loinc.org",
    "display": "Hematocrit",
}
LOINC_ERYTHROCYTES = {
    "code": "LA12896-9",
    "system": "http://loinc.org",
    "display": "Erythrocytes",
}
LOINC_PLATELETS = {
    "code": "LP7631-7",
    "system": "http://loinc.org",
    "display": "Platelets",
}
LOINC_LIPID_PANEL = {
    "code": "LP97557-0",
    "system": "http://loinc.org",
    "display": "Lipid panel with direct LDL",
}
LOINC_URINE = {
    "code": "LP7681-2",
    "system": "http://loinc.org",
    "display": "Urine",
}

DEFAULT_PRICE_COMPONENTS = [
    {
        "code": {
            "code": "oldage",
            "system": "http://ohc.network/codes/monetary/discount",
            "display": "Old Age Discount",
        },
        "factor": 10.0,
        "monetary_component_type": "discount",
    },
    {
        "code": {
            "code": "igst",
            "system": "http://ohc.network/codes/monetary/tax",
            "display": "IGST",
        },
        "factor": 6.0,
        "monetary_component_type": "tax",
    },
    {
        "code": {
            "code": "gst",
            "system": "http://ohc.network/codes/monetary/tax",
            "display": "GST",
        },
        "factor": 6.0,
        "monetary_component_type": "tax",
    },
]


def build_price_components(base_amount, extra=None, include_defaults=False):
    """Build a full price_components list from base amount + optional extras."""
    components = [{"amount": base_amount, "monetary_component_type": "base"}]
    if extra:
        components.extend(extra)
    if include_defaults:
        components.extend(DEFAULT_PRICE_COMPONENTS)
    return components


ORAL_TABLET_DEFINITIONAL = {
    "dosage_form": SNOMED_ORAL_TABLET,
    "intended_routes": [SNOMED_ORAL_ROUTE],
}

DEFAULT_STORAGE_GUIDELINES = [
    {
        "note": "Store in a cool, dry place away from direct sunlight.",
        "stability_duration": {
            "unit": UCUM_YEAR,
            "value": 5,
        },
    }
]


def make_range(label, *, low=None, high=None):
    r = {"interpretation": {"display": label}}
    if low is not None:
        r["min"] = low
    if high is not None:
        r["max"] = high
    return r


def simple_ranges(low_max, normal_max, high_min=None):
    high_min = high_min or normal_max
    return [
        {
            "conditions": [],
            "ranges": [
                make_range("Low", high=low_max),
                make_range("Normal", low=low_max, high=normal_max),
                make_range("High", low=high_min),
            ],
        }
    ]


def make_container(
    cap,
    capacity_ml,
    description,
    preparation,
    min_volume_ml,
    is_derived=False,
    preference="preferred",
    single_use=False,
):
    return {
        "cap": cap,
        "capacity": {"unit": UCUM_ML, "value": capacity_ml},
        "description": description,
        "preparation": preparation,
        "minimum_volume": {"quantity": {"unit": UCUM_ML, "value": min_volume_ml}},
    }


def make_type_tested(
    container,
    *,
    is_derived=False,
    preference="preferred",
    single_use=False,
    requirement,
    retention_unit,
    retention_value,
):
    return {
        "container": container,
        "is_derived": is_derived,
        "preference": preference,
        "single_use": single_use,
        "requirement": requirement,
        "retention_time": {"unit": retention_unit, "value": retention_value},
    }


LAB_TESTS = [
    {
        "specimen": {
            "title": "Blood Glucose Test Specimen",
            "description": (
                "A venous blood specimen collected for the quantitative "
                "measurement of glucose concentration in blood."
            ),
            "type_collected": HL7_BLDV,
            "patient_preparation": [SNOMED_AFTER_FASTING],
            "collection": SNOMED_PUNCTURE,
            "type_tested": make_type_tested(
                make_container(
                    HL7_GREY_CAP,
                    5.0,
                    "Grey-top collection tube containing "
                    "sodium fluoride/potassium oxalate.",
                    "Label tube immediately after collection. "
                    "Invert gently 8-10 times to mix anticoagulant.",
                    2.0,
                ),
                requirement=(
                    "Refrigerated (2-8°C). Specimen must be centrifuged and "
                    "plasma separated within 2 hours of collection."
                ),
                retention_unit=UCUM_H,
                retention_value=24,
            ),
        },
        "observation": {
            "title": "Fasting Blood Glucose",
            "code": LOINC_FASTING_GLUCOSE,
            "category": ObservationCategoryChoices.laboratory.value,
            "permitted_data_type": QuestionType.quantity.value,
            "description": (
                "Measures the concentration of glucose in plasma "
                "after 8-12 hours of fasting."
            ),
            "qualified_ranges": simple_ranges(70, 99, 100),
        },
        "charge_item_definition": {
            "title": "Fasting Blood Glucose Test",
            "price_components": build_price_components(600.0, include_defaults=True),
            "description": (
                "Measures the concentration of glucose in plasma "
                "after 8-12 hours of fasting."
            ),
            "purpose": (
                "Measures the concentration of glucose in plasma "
                "after 8-12 hours of fasting."
            ),
        },
        "activity": {
            "title": "Fasting Blood Glucose",
            "code": SNOMED_FASTING_GLUCOSE,
            "description": (
                "Measures the concentration of glucose in plasma "
                "after 8-12 hours of fasting."
            ),
            "usage": (
                "Measures the concentration of glucose in plasma "
                "after 8-12 hours of fasting."
            ),
            "diagnostic_report_codes": [LOINC_FASTING_GLUCOSE],
        },
    },
    {
        "specimen": {
            "title": "CBC Blood Specimen",
            "description": (
                "Whole blood specimen collected via venipuncture "
                "for performing a Complete Blood Count (CBC) test."
            ),
            "type_collected": HL7_BLDV,
            "patient_preparation": [],
            "collection": SNOMED_PUNCTURE,
            "type_tested": make_type_tested(
                make_container(
                    HL7_LAVENDER_CAP,
                    10.0,
                    "Purple top EDTA tube",
                    "Invert gently 8-10 times immediately after "
                    "collection to mix with anticoagulant.",
                    3.0,
                ),
                is_derived=True,
                single_use=True,
                requirement=(
                    "Collected in EDTA tube to prevent clotting.\n"
                    "Should be processed within 6 hours of collection."
                ),
                retention_unit=UCUM_H,
                retention_value=6,
            ),
        },
        "observation": {
            "title": "Complete Blood Count",
            "code": LOINC_CBC_PANEL,
            "category": ObservationCategoryChoices.laboratory.value,
            "permitted_data_type": QuestionType.quantity.value,
            "description": (
                "A Complete Blood Count (CBC) evaluates overall health "
                "status by measuring multiple blood components."
            ),
            "method": SNOMED_AUTOMATED_COUNT,
            "permitted_unit": UCUM_G_DL,
            "qualified_ranges": [],
            "component": [
                {
                    "code": LOINC_HEMOGLOBIN,
                    "permitted_unit": UCUM_G_DL,
                    "permitted_data_type": QuestionType.quantity.value,
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=12),
                                make_range("Normal", low=12, high=16),
                                make_range("High", low=16),
                            ],
                        },
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=14),
                                make_range("Normal", low=14, high=18),
                                make_range("High", low=18),
                            ],
                        },
                    ],
                },
                {
                    "code": LOINC_HEMATOCRIT,
                    "permitted_unit": UCUM_PERCENT,
                    "permitted_data_type": QuestionType.quantity.value,
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=36),
                                make_range("Normal", low=36, high=48),
                                make_range("High", low=48),
                            ],
                        },
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=40),
                                make_range("Normal", low=40, high=52),
                                make_range("High", low=52),
                            ],
                        },
                    ],
                },
                {
                    "code": LOINC_ERYTHROCYTES,
                    "permitted_unit": UCUM_MILLION_PER_UL,
                    "permitted_data_type": QuestionType.quantity.value,
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=4.0),
                                make_range("Normal", low=4.0, high=6.0),
                                make_range("High", low=6.0),
                            ],
                        },
                    ],
                },
                {
                    "code": LOINC_PLATELETS,
                    "permitted_unit": UCUM_THOUSANDS_PER_UL,
                    "permitted_data_type": QuestionType.quantity.value,
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                make_range("Low", high=150),
                                make_range("Normal", low=150, high=450),
                                make_range("High", low=450),
                            ],
                        },
                    ],
                },
            ],
        },
        "charge_item_definition": {
            "title": "Complete Blood Count (CBC) Test",
            "price_components": build_price_components(
                450.0,
                extra=[
                    {
                        "code": {
                            "code": "child",
                            "system": "http://ohc.network/codes/monetary/discount",
                            "display": "Child Discount",
                        },
                        "factor": 5.0,
                        "monetary_component_type": "discount",
                    },
                ],
                include_defaults=True,
            ),
            "description": (
                "A Complete Blood Count (CBC) evaluates overall health "
                "status by measuring multiple blood components."
            ),
            "purpose": (
                "A Complete Blood Count (CBC) evaluates overall health "
                "status by measuring multiple blood components."
            ),
        },
        "activity": {
            "title": "Complete Blood Count (CBC) Panel",
            "code": SNOMED_CBC,
            "description": (
                "A Complete Blood Count (CBC) evaluates overall health "
                "status by measuring multiple blood components."
            ),
            "usage": (
                "Evaluates the overall health status by measuring "
                "multiple blood components."
            ),
            "diagnostic_report_codes": [LOINC_CBC_PANEL],
        },
    },
    {
        "specimen": {
            "title": "Lipid Panel Blood Specimen",
            "description": (
                "Venous blood specimen collected to evaluate cholesterol "
                "levels including total cholesterol, HDL, LDL, and triglycerides."
            ),
            "type_collected": HL7_BLDV,
            "patient_preparation": [SNOMED_AFTER_FASTING],
            "collection": SNOMED_PUNCTURE,
            "type_tested": make_type_tested(
                make_container(
                    HL7_DARK_YELLOW_CAP,
                    5.0,
                    "Serum separator tube (SST, Gold-top)",
                    "Invert tube gently 5-6 times. Let stand upright "
                    "for clotting. Centrifuge within 1 hour.",
                    2.0,
                ),
                single_use=True,
                requirement=(
                    "Refrigerated (2-8°C). Allow blood to clot at room "
                    "temperature for 30 minutes."
                ),
                retention_unit=UCUM_D,
                retention_value=7,
            ),
        },
        "observation": {
            "title": "Lipid Panel Observation",
            "code": LOINC_LIPID_PANEL,
            "category": ObservationCategoryChoices.laboratory.value,
            "permitted_data_type": QuestionType.quantity.value,
            "description": (
                "A comprehensive blood test measuring cholesterol and "
                "triglyceride levels to assess cardiovascular health."
            ),
            "qualified_ranges": [
                {
                    "conditions": [],
                    "ranges": [
                        make_range("Desirable", high=200),
                        make_range("Borderline High", low=200, high=239),
                        make_range("High", low=239),
                    ],
                },
            ],
        },
        "charge_item_definition": {
            "title": "Lipid Panel Test",
            "price_components": build_price_components(400.0, include_defaults=True),
            "derived_from_uri": "urn:chargeitem:lipid-panel",
            "description": (
                "Comprehensive blood test measuring cholesterol and "
                "triglyceride levels."
            ),
            "purpose": "Billing for lipid panel diagnostic service.",
        },
        "activity": {
            "title": "Lipid Panel",
            "code": SNOMED_LIPID_PANEL,
            "derived_from_uri": "urn:activity:lipid-panel",
            "description": (
                "A comprehensive blood test measuring cholesterol and "
                "triglyceride levels."
            ),
            "usage": (
                "A comprehensive blood test measuring cholesterol and "
                "triglyceride levels."
            ),
            "diagnostic_report_codes": [LOINC_LIPID_PANEL],
        },
    },
    {
        "specimen": {
            "title": "Urinalysis Specimen",
            "description": (
                "Midstream clean-catch urine specimen collected for "
                "analysis of physical, chemical, and microscopic properties."
            ),
            "type_collected": HL7_UR,
            "patient_preparation": [SNOMED_SAME_DAY_BEFORE],
            "collection": SNOMED_URINE_CLEAN_CATCH,
            "type_tested": make_type_tested(
                make_container(
                    HL7_YELLOW_CAP,
                    100.0,
                    "Sterile urine collection container with screw cap.",
                    "Label container. Ensure tight seal to "
                    "avoid contamination or leakage.",
                    30.0,
                ),
                requirement=(
                    "Up to 24 hours refrigerated. Deliver to lab "
                    "within 2 hours of collection."
                ),
                retention_unit=UCUM_H,
                retention_value=2,
            ),
        },
        "observation": {
            "title": "Urinalysis Observation",
            "code": LOINC_URINE,
            "category": ObservationCategoryChoices.laboratory.value,
            "permitted_data_type": QuestionType.choice.value,
            "description": (
                "A diagnostic test analyzing urine's physical, chemical, "
                "and microscopic properties."
            ),
            "method": SNOMED_URINE_DIPSTICK,
            "qualified_ranges": [],
        },
        "charge_item_definition": {
            "title": "Urinalysis Test",
            "price_components": build_price_components(
                500.0,
                extra=[
                    {"amount": 15.55, "monetary_component_type": "discount"},
                    {
                        "code": {
                            "code": "cgst",
                            "system": "http://ohc.network/codes/monetary/tax",
                            "display": "CGST",
                        },
                        "factor": 3.0,
                        "monetary_component_type": "tax",
                    },
                ],
                include_defaults=True,
            ),
            "derived_from_uri": "urn:chargeitem:urinalysis",
            "description": (
                "Diagnostic test analyzing urine's physical, chemical, "
                "and microscopic properties."
            ),
            "purpose": "Billing for urinalysis diagnostic service.",
        },
        "activity": {
            "title": "Urinalysis",
            "code": SNOMED_URINE_EVAL,
            "description": (
                "A diagnostic test analyzing urine's physical, chemical, "
                "and microscopic properties."
            ),
            "usage": (
                "A diagnostic test analyzing urine's physical, chemical, "
                "and microscopic properties."
            ),
            "diagnostic_report_codes": [LOINC_URINE],
        },
    },
]

INVENTORY_ITEMS = [
    {
        "category": "Medications",
        "product_knowledge": {
            "name": "Amoxicillin",
            "base_unit": UCUM_TABLET,
            "code": SNOMED_AMOXICILLIN,
            "definitional": ORAL_TABLET_DEFINITIONAL,
            "storage_guidelines": DEFAULT_STORAGE_GUIDELINES,
        },
        "charge_item_definition": {
            "title": "Amoxicillin 500mg Capsule",
            "price_components": build_price_components(50.0),
        },
        "product_extras": {
            "batch": {"lot_number": "AMX-2026-001"},
            "expiration_date": "2027-12-31T00:00:00Z",
            "purchase_price": "30.00",
            "standard_pack_size": 10,
        },
        "stock_quantity": 20,
    },
    {
        "category": "Medications",
        "product_knowledge": {
            "name": "Paracetamol",
            "base_unit": UCUM_TABLET,
            "code": SNOMED_PARACETAMOL,
            "definitional": ORAL_TABLET_DEFINITIONAL,
            "storage_guidelines": DEFAULT_STORAGE_GUIDELINES,
        },
        "charge_item_definition": {
            "title": "Paracetamol 500mg Tablet",
            "price_components": build_price_components(20.0),
        },
        "product_extras": {
            "batch": {"lot_number": "PCM-2026-014"},
            "expiration_date": "2028-06-30T00:00:00Z",
            "purchase_price": "12.00",
            "standard_pack_size": 10,
        },
        "stock_quantity": 50,
    },
    {
        "category": "Medications",
        "product_knowledge": {
            "name": "Ibuprofen",
            "base_unit": UCUM_TABLET,
            "code": SNOMED_IBUPROFEN,
            "definitional": ORAL_TABLET_DEFINITIONAL,
            "storage_guidelines": DEFAULT_STORAGE_GUIDELINES,
        },
        "charge_item_definition": {
            "title": "Ibuprofen 400mg Tablet",
            "price_components": build_price_components(30.0),
        },
        "product_extras": {
            "batch": {"lot_number": "IBU-2026-007"},
            "expiration_date": "2027-09-30T00:00:00Z",
            "purchase_price": "18.00",
            "standard_pack_size": 10,
        },
        "stock_quantity": 30,
    },
    {
        "category": "Consumables",
        "product_knowledge": {
            "name": "Gloves",
            "base_unit": UCUM_COUNT,
            "product_type": ProductTypeOptions.consumable.value,
            "code": SNOMED_GLOVES,
            "storage_guidelines": DEFAULT_STORAGE_GUIDELINES,
        },
        "charge_item_definition": {
            "title": "Pair of Gloves",
            "price_components": build_price_components(5.0),
        },
        "product_extras": {
            "batch": {"lot_number": "GLV-2026-022"},
            "expiration_date": "2029-01-31T00:00:00Z",
            "purchase_price": "3.00",
            "standard_pack_size": 100,
        },
        "stock_quantity": 15,
    },
]

MANAGING_ORG_USERS = [
    # action: "create" creates a new user and assigns the role
    # action: "assign" looks up an existing user and assigns the role
    {"action": "create", "username": "care-role-admin", "role": "Admin"},
    {"action": "create", "username": "care-role-manager", "role": "Manager"},
    {"action": "create", "username": "care-role-member", "role": "Member"},
    {"action": "assign", "username": "care-admin", "role": "Admin"},
    {"action": "assign", "username": "admin", "role": "Admin"},
    {"action": "assign", "username": "care-doctor", "role": "Manager"},
]

FACILITY_DEPARTMENTS = [
    "General Medicine",
    "Emergency",
    "Laboratory",
    "Pharmacy",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Pediatrics",
    "Obstetrics & Gynecology",
    "Dermatology",
    "Ophthalmology",
    "ENT",
    "Radiology",
    "Oncology",
    "Psychiatry",
    "Nephrology",
    "Pulmonology",
    "Gastroenterology",
    "Urology",
    "Endocrinology",
]

# Default availability: Mon-Sun 09:30-18:30, 18-minute appointment slots, 3 tokens per slot
DEFAULT_AVAILABILITY = {
    "name": "Default Availability",
    "slot_type": "appointment",
    "slot_size_in_minutes": 18,
    "tokens_per_slot": 3,
    "reason": "",
    "availability": [
        {"day_of_week": day, "start_time": "09:30", "end_time": "18:30"}
        for day in range(7)
    ],
}
