ITEMS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "price": {"type": "number"},
                "category": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["id", "name", "price"],
        }
    ],
}
