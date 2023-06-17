CONTENT = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "content": [
        {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "data": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["type", "data"],
        }
    ],
}
