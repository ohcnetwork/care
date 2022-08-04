HL7_META = {
    "type": "object",
    "required": ["local_ip_address", "middleware_hostname"],
    "properties": {
        "local_ip_address": {"type": "string"},
        "middleware_hostname": {"type": "string"},
        "insecure_connection": {"type": "boolean"},
    },
    "additionalProperties": False,
}

ONVIF_META = {
    "type": "object",
    "required": [
        "local_ip_address",
        "middleware_hostname",
        "camera_access_key",
        "camera_type",
    ],
    "properties": {
        "local_ip_address": {"type": "string"},
        "middleware_hostname": {"type": "string"},
        "camera_access_key": {"type": "string"},
        "camera_type": {"type": "string"},
        "insecure_connection": {"type": "boolean"},
    },
    "additionalProperties": False,
}

EMPTY_META = {"type": "object", "additionalProperties": False}

ASSET_META = {
    "$schema": f"http://json-schema.org/draft-07/schema#",
    "anyOf": [
        {"$ref": "#/definitions/onvif"},
        {"$ref": "#/definitions/hl7monitor"},
        {"$ref": "#/definitions/empty"},
    ],
    "definitions": {"onvif": ONVIF_META, "hl7monitor": HL7_META, "empty": EMPTY_META},
}
