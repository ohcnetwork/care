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

VACCINATION = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "vaccine": {"type": "string"},
                "doses": {"type": "number", "default": 0},
                "last_vaccinated_date": {"type": "string"},
            },
            "additionalProperties": False,
            "required": [
                "vaccine",
                "doses",
                "last_vaccinated_date",
            ],
        }
    ],
}
