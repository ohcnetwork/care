import environ

from care.emr.resources.utils import MonetaryCodes, MonetaryComponentDefinitions

env = environ.Env()

MAX_DATAPOINTS_PER_UPSERT = env.int("MAX_DATAPOINTS_PER_UPSERT", default=100)

MAX_APPOINTMENTS_PER_PATIENT = env.int("MAX_APPOINTMENTS_PER_PATIENT", default=10)

MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY = env.int(
    "MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY", default=5
)

# Maximum file upload size in MB
MAX_FILE_UPLOAD_SIZE = env.int("MAX_FILE_UPLOAD_SIZE", default=5)

LOCATION_MAX_DEPTH = env.int("LOCATION_MAX_DEPTH", default=10)

ORGANIZATION_MAX_DEPTH = env.int("ORGANIZATION_MAX_DEPTH", default=10)

FACILITY_ORGANIZATION_MAX_DEPTH = env.int("FACILITY_ORGANIZATION_MAX_DEPTH", default=10)

MAX_LOCATION_IN_FACILITY = env.int("MAX_LOCATION_IN_FACILITY", default=1000)

MAX_ORGANIZATION_IN_FACILITY = env.int("MAX_ORGANIZATION_IN_FACILITY", default=1000)

MAX_SLOTS_PER_AVAILABILITY = env.int("MAX_SLOTS_PER_AVAILABILITY", default=30)

MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE = env.int(
    "MAX_QUESTIONNAIRE_TEXT_RESPONSE_SIZE", default=2500
)

TAX_CODES = MonetaryCodes(
    env.json(
        "TAX_CODES",
        default=[
            {
                "code": "igst",
                "display": "IGST",
                "system": "http://ohc.network/codes/monetary/tax",
            },
            {
                "code": "cgst",
                "display": "CGST",
                "system": "http://ohc.network/codes/monetary/tax",
            },
            {
                "code": "sgst",
                "display": "SGST",
                "system": "http://ohc.network/codes/monetary/tax",
            },
            {
                "code": "utgst",
                "display": "UTGST",
                "system": "http://ohc.network/codes/monetary/tax",
            },
        ],
    )
)

TAX_MONETARY_COMPONENT_DEFINITIONS = MonetaryComponentDefinitions(
    env.json(
        "TAX_MONETARY_COMPONENT_DEFINITIONS",
        default=[
            # 18% Slab
            {
                "title": "CGST @ 9",
                "code": {
                    "code": "cgst",
                    "display": "CGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 9,
            },
            {
                "title": "SGST @ 9",
                "code": {
                    "code": "sgst",
                    "display": "SGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 9,
            },
            {
                "title": "IGST @ 18",
                "code": {
                    "code": "igst",
                    "display": "IGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 18,
            },
            # 12% slab
            {
                "title": "CGST @ 6",
                "code": {
                    "code": "cgst",
                    "display": "CGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 6,
            },
            {
                "title": "SGST @ 6",
                "code": {
                    "code": "sgst",
                    "display": "SGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 6,
            },
            {
                "title": "IGST @ 12",
                "code": {
                    "code": "igst",
                    "display": "IGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 12,
            },
            # 5% Slab
            {
                "title": "CGST @ 2.5",
                "code": {
                    "code": "cgst",
                    "display": "CGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 2.5,
            },
            {
                "title": "SGST @ 2.5",
                "code": {
                    "code": "sgst",
                    "display": "SGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 2.5,
            },
            {
                "title": "IGST @ 5",
                "code": {
                    "code": "igst",
                    "display": "IGST",
                    "system": "http://ohc.network/codes/monetary/tax",
                },
                "monetary_component_type": "tax",
                "factor": 5,
            },
        ],
    )
)

DISCOUNT_CODES = MonetaryCodes(
    env.json(
        "DISCOUNT_CODES",
        default=[
            {
                "code": "oldage",
                "display": "Old Age Discount",
                "system": "http://ohc.network/codes/monetary/discount",
            },
            {
                "code": "child",
                "display": "Child Discount",
                "system": "http://ohc.network/codes/monetary/discount",
            },
            {
                "code": "student",
                "display": "Student Discount",
                "system": "http://ohc.network/codes/monetary/discount",
            },
        ],
    )
)

DISCOUNT_MONETARY_COMPONENT_DEFINITIONS = MonetaryComponentDefinitions(
    env.json(
        "DISCOUNT_MONETARY_COMPONENT_DEFINITIONS",
        default=[
            {
                "title": "Old Age Discount",
                "code": {
                    "code": "oldage",
                    "display": "Old Age Discount",
                    "system": "http://ohc.network/codes/monetary/discount",
                },
                "monetary_component_type": "discount",
                "factor": 10,
            },
            {
                "title": "Child Discount",
                "code": {
                    "code": "child",
                    "display": "Child Discount",
                    "system": "http://ohc.network/codes/monetary/discount",
                },
                "monetary_component_type": "discount",
                "factor": 10,
            },
        ],
    )
)


INFORMATIONAL_MONETARY_CODES = MonetaryCodes(
    env.json(
        "INFORMATIONAL_MONETARY_CODES",
        default=[
            {
                "code": "mrp",
                "display": "MRP",
                "system": "http://ohc.network/codes/monetary/informational",
            }
        ],
    )
)
