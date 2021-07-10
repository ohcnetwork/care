DATETIME_REGEX = "^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?)$"

LINES_CATHETERS = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "pattern": DATETIME_REGEX},
                "type": {"type": "string"},
                "site": {"type": "string"},
            },
            "required": ["start_date", "types", "site"],
        }
    ],
}
