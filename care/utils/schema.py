from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema


class AutoSchema(SpectacularAutoSchema):
    def get_tags(self):
        tokenized_path = self._tokenize_path()
        # use last non-parameter path part as default tag
        return [tokenized_path[-1]]


meta_object_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "local_ip_address": {"type": "string", "format": "ipv4"},
        "middleware_hostname": {"type": "string"},
        "insecure_connection": {"type": "boolean", "default": False},
        "camera_access_key": {
            "type": "string",
            "pattern": "^[^:]+:[^:]+:[^:]+$",  # valid pattern for "abc:def:ghi" , "123:456:789"
        },
    },
    "required": ["local_ip_address", "middleware_hostname"],
    "allOf": [
        {
            "if": {"properties": {"_name": {"const": "onvif"}}},
            "then": {
                "properties": {"camera_access_key": {"type": "string"}},
                "required": [
                    "camera_access_key"
                ],  # Require camera_access_key for Onvif
            },
            "else": {
                "properties": {"id": {"type": "string"}},
                "required": ["id"],  # Require id for non-Onvif assets
                "not": {
                    "required": [
                        "camera_access_key"
                    ]  # Make camera_access_key not required for non-Onvif
                },
            },
        }
    ],
}
