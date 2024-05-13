BLOOD_PRESSURE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "systolic": {"type": "number"},
        "diastolic": {"type": "number"},
        "mean": {"type": "number"},
    },
    "additionalProperties": False,
}

INFUSIONS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
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
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "quantity": {"type": "number"},
            },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

FEED = {
    "$schema": "http://json-schema.org/draft-07/schema#",
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
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "quantity": {"type": "number"},
            },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

PRESSURE_SORE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "base_score": {"type": "number"},
                "length": {"type": "number"},
                "width": {"type": "number"},
                "exudate_amount": {"enum": ["None", "Light", "Moderate", "Heavy"]},
                "tissue_type": {
                    "enum": [
                        "Closed",
                        "Epithelial",
                        "Granulation",
                        "Slough",
                        "Necrotic",
                    ]
                },
                "description": {"type": "string"},
                "push_score": {"type": "number"},
                "region": {"type": "string"},
                "scale": {"type": "number", "minimum": 1, "maximum": 5},
            },
            "additionalProperties": False,
            "required": [],
        }
    ],
}

PAIN_SCALE_ENHANCED = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "scale": {"type": "number", "minimum": 1, "maximum": 10},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
            "required": ["region", "scale"],
        }
    ],
}

NURSING_PROCEDURE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
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
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {"dialysis": {"type": "boolean"}},
    "additionalProperties": False,
}
