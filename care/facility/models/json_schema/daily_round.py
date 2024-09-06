BLOOD_PRESSURE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "definitions": {
        "blood-pressure": {"type": "number", "minimum": 0, "maximum": 400},
    },
    "properties": {
        "systolic": {},
        "diastolic": {},
        "systolic_recordable": {"type": "boolean"},
        "diastolic_recordable": {"type": "boolean"},
    },
    "required": ["systolic_recordable", "diastolic_recordable"],
    "allOf": [
        {
            "if": {
                "properties": {"systolic_recordable": {"const": True}},
            },
            "then": {
                "properties": {"systolic": {"$ref": "#/definitions/blood-pressure"}},
                "required": ["systolic"],
            },
            "else": {
                "properties": {"systolic": {"const": None}},
            },
        },
        {
            "if": {
                "properties": {"diastolic_recordable": {"const": True}},
            },
            "then": {
                "properties": {"diastolic": {"$ref": "#/definitions/blood-pressure"}},
                "required": ["diastolic"],
            },
            "else": {
                "properties": {"diastolic": {"const": None}},
            },
        },
    ],
    "additionalProperties": False,
}

INFUSIONS = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "name": {
                    "enum": [
                        "Adrenalin",
                        "Nor-adrenalin",
                        "Vasopressin",
                        "Dopamine",
                        "Dobutamine",
                    ]
                },
                "quantity": {"type": "number", "minimum": 0},
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
                "name": {"enum": ["RL", "NS", "DNS"]},
                "quantity": {"type": "number", "minimum": 0},
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
                "name": {"enum": ["Ryles Tube", "Normal Feed"]},
                "quantity": {"type": "number", "minimum": 0},
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
                "name": {
                    "enum": [
                        "Urine",
                        "Ryles Tube Aspiration",
                        "ICD",
                        "Abdominal Drain",
                    ],
                },
                "quantity": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
            "required": ["name", "quantity"],
        }
    ],
}

HUMAN_BODY_REGIONS = [
    "AnteriorHead",
    "AnteriorNeck",
    "AnteriorRightShoulder",
    "AnteriorRightChest",
    "AnteriorRightArm",
    "AnteriorRightForearm",
    "AnteriorRightHand",
    "AnteriorLeftHand",
    "AnteriorLeftChest",
    "AnteriorLeftShoulder",
    "AnteriorLeftArm",
    "AnteriorLeftForearm",
    "AnteriorRightFoot",
    "AnteriorLeftFoot",
    "AnteriorRightLeg",
    "AnteriorLowerChest",
    "AnteriorAbdomen",
    "AnteriorLeftLeg",
    "AnteriorRightThigh",
    "AnteriorLeftThigh",
    "AnteriorGroin",
    "PosteriorHead",
    "PosteriorNeck",
    "PosteriorLeftChest",
    "PosteriorRightChest",
    "PosteriorAbdomen",
    "PosteriorLeftShoulder",
    "PosteriorRightShoulder",
    "PosteriorLeftArm",
    "PosteriorLeftForearm",
    "PosteriorLeftHand",
    "PosteriorRightArm",
    "PosteriorRightForearm",
    "PosteriorRightHand",
    "PosteriorLeftThighAndButtock",
    "PosteriorRightThighAndButtock",
    "PosteriorLeftLeg",
    "PosteriorRightLeg",
    "PosteriorLeftFoot",
    "PosteriorRightFoot",
]

PRESSURE_SORE = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": [
        {
            "type": "object",
            "properties": {
                "length": {"type": "number", "minimum": 0},
                "width": {"type": "number", "minimum": 0},
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
                "push_score": {"type": "number", "minimum": 0, "maximum": 19},
                "region": {"enum": HUMAN_BODY_REGIONS},
                "scale": {"type": "number", "minimum": 1, "maximum": 5},
            },
            "additionalProperties": False,
            "required": ["region", "width", "length"],
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
                "region": {"enum": HUMAN_BODY_REGIONS},
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
                "procedure": {
                    "enum": [
                        "personal_hygiene",
                        "positioning",
                        "suctioning",
                        "ryles_tube_care",
                        "iv_sitecare",
                        "nubulisation",
                        "dressing",
                        "dvt_pump_stocking",
                        "restrain",
                        "chest_tube_care",
                        "tracheostomy_care",
                        "stoma_care",
                        "catheter_care",
                    ],
                },
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
