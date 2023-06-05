HL7_META = {
    "type": "object",
    "required": ["local_ip_address"],
    "properties": {
        "local_ip_address": {"type": "string"},
        "middleware_hostname": {"type": "string"},
        "asset_type": {"type": "string"},
        "insecure_connection": {"type": "boolean"},
    },
    "additionalProperties": False,
}

VENTILATOR_META = {
    "type": "object",
    "required": ["local_ip_address"],
    "properties": {
        "local_ip_address": {"type": "string"},
        "middleware_hostname": {"type": "string"},
        "asset_type": {"type": "string"},
        "insecure_connection": {"type": "boolean"},
    },
    "additionalProperties": False,
}

ONVIF_META = {
    "type": "object",
    "required": ["local_ip_address", "camera_access_key"],
    "properties": {
        "local_ip_address": {"type": "string"},
        "middleware_hostname": {"type": "string"},
        "camera_access_key": {"type": "string"},
        "camera_type": {"type": "string"},
        "asset_type": {"type": "string"},
        "insecure_connection": {"type": "boolean"},
    },
    "additionalProperties": False,
}

EMPTY_META = {"type": "object", "additionalProperties": False}

ASSET_META = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "anyOf": [
        {"$ref": "#/definitions/onvif"},
        {"$ref": "#/definitions/hl7monitor"},
        {"$ref": "#/definitions/empty"},
    ],
    "definitions": {
        "onvif": ONVIF_META,
        "hl7monitor": HL7_META,
        "ventilator": VENTILATOR_META,
        "empty": EMPTY_META,
    },
}
