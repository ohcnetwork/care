BLOOD_PRESSURE = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "systolic": {"type": "number"},
        "diastolic": {"type": "number"},
        "mean": {"type": "number"},
    },
    "additionalProperties": False,
}

INFUSIONS = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "quantity": {"type": "number"},
                "concentration": {"type": "number"},
                "conc_unit": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

IV_FLUID = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {"name": {"type": "string"}, "quantity": {"type": "number"}, },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

FEED = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "quantity": {"type": "number"},
                "calories": {"type": "number"},
            },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

OUTPUT = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {"name": {"type": "string"}, "quantity": {"type": "number"}, },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

PRESSURE_SORE = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "scale": {"type": "number", "minimum": 1, "maximum": 5},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["region", "scale"],
        }
    ],
}

PAIN_SCALE_ENHANCED = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "scale": {"type": "number", "minimum": 1, "maximum": 5},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["region", "scale"],
        }
    ],
}

NURSING_PROCEDURE = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "procedure": {"type": "string"},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["procedure", "description"],
        }
    ],
}

META = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {"dialysis": {"type": "boolean"}},
    "additionalProperties": False,
}
