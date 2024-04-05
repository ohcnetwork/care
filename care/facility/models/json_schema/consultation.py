from care.facility.models.json_schema.common import DATETIME_REGEX

LINES_CATHETERS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "pattern": DATETIME_REGEX},
                "type": {"type": "string"},
                "site": {"type": "string"},
                "other_type": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["start_date", "type", "site"],
        }
    ],
}

CONSENT_RECORDS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "number"},
                "patient_code_status": {"type": "number"},
                "deleted": {"type": "boolean"},
            },
            "additionalProperties": False,
            "required": ["id", "type"],
        }
    ],
}
