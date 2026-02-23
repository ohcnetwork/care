import environ

from care.emr.resources.utils import MonetaryCodes, MonetaryComponentDefinitions

env = environ.Env()

MAX_DATAPOINTS_PER_UPSERT = env.int("MAX_DATAPOINTS_PER_UPSERT", default=100)

MAX_REQUESTS_PER_BATCH_REQUEST = env.int("MAX_REQUESTS_PER_BATCH_REQUEST", default=20)

MAX_APPOINTMENTS_PER_PATIENT = env.int("MAX_APPOINTMENTS_PER_PATIENT", default=10)

MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY = env.int(
    "MAX_ACTIVE_ENCOUNTERS_PER_PATIENT_IN_FACILITY", default=5
)

PASSWORD_RESET_TOKEN_TTL_HOURS = env.int("PASSWORD_RESET_TOKEN_TTL_HOURS", default=24)

MAX_FAVORITES_PER_LIST = env.int("MAX_FAVORITES_PER_LIST", default=50)

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


# Patient Identifier Configs

MAINTAIN_PATIENT_NAME_IDENTIFIER = env.bool(
    "MAINTAIN_PATIENT_NAME_IDENTIFIER", default=False
)

MAINTAIN_PATIENT_PHONE_NUMBER_IDENTIFIER = env.bool(
    "MAINTAIN_PATIENT_PHONE_NUMBER_IDENTIFIER", default=False
)

MAINTAIN_FACILITY_PATIENT_NAME_IDENTIFIER = env.bool(
    "MAINTAIN_FACILITY_PATIENT_NAME_IDENTIFIER", default=True
)

PATIENT_NAME_MAX_LENGTH = env.int("PATIENT_NAME_MAX_LENGTH", default=75)


# Encounter Config

ENCOUNTER_RESTART_TIME_LIMIT_HOURS = env.int(
    "ENCOUNTER_RESTART_TIME_LIMIT_HOURS", default=0
)

INVOICE_FREE_CANCEL_PERIOD_MINUTES = env.int(
    "INVOICE_FREE_CANCEL_PERIOD_MINUTES", default=0
)

CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES = env.int(
    "CHARGE_ITEM_FREE_CANCEL_PERIOD_MINUTES", default=0
)

PAYMENT_RECONCILIATION_FREE_CANCEL_PERIOD_MINUTES = env.int(
    "PAYMENT_RECONCILIATION_FREE_CANCEL_PERIOD_MINUTES", default=0
)

# Rounding

ACCOUNTING_PRECISION = env.int("ACCOUNTING_PRECISION", default=2)

ACCOUNTING_ROUNDING_METHOD = env(
    "ACCOUNTING_ROUNDING_METHOD", default="care.utils.rounding.RoundingHalfUp"
)


INVOICE_FINAL_AMOUNT_PRECISION = env.int("INVOICE_FINAL_AMOUNT_PRECISION", default=0)

INVOICE_FINAL_AMOUNT_ROUNDING_METHOD = env(
    "INVOICE_FINAL_AMOUNT_ROUNDING_METHOD", default="care.utils.rounding.RoundingHalfUp"
)

PATIENT_GLOBAL_EDIT_ACCESS_ENABLED = env.bool(
    "PATIENT_GLOBAL_EDIT_ACCESS_ENABLED", default=False
)

PREFERENCE_SCHEMA = env.json(
    "PREFERENCE_SCHEMA",
    default={
        "facility_quick_links": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "UserPreferences",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "blacklist": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "default": [],
                },
                "custom_links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["link", "title"],
                        "properties": {
                            "link": {"type": "string", "minLength": 1},
                            "title": {"type": "string", "minLength": 1},
                            "icon": {"type": "string", "minLength": 1},
                            "facilityId": {"type": "string", "minLength": 1},
                        },
                    },
                    "default": [],
                },
            },
        }
    },
)

QUESTIONNAIRE_ERRORED_TIME_LIMIT_MINUTES = env.int(
    "QUESTIONNAIRE_ERRORED_TIME_LIMIT_MINUTES", default=120
)
