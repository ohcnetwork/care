from pydantic import field_validator


def validate_extensions(data, resource_type):
    from care.emr.registries.extensions.registry import ExtensionRegistry

    if data is None or not isinstance(data, dict):
        raise ValueError("Invalid extensions data")
    cleaned_data = {}
    for key in data:
        extension_handler = ExtensionRegistry.get_extension_obj(resource_type, key)
        if extension_handler is None:
            # TODO: Once stable, raise error instead
            continue
        extension_handler.validate(data[key])
        cleaned_data[key] = extension_handler.serialize_extensions(data[key])
    return cleaned_data


class ExtensionValidator:
    # ___extension_resource_type__ = None

    extensions: dict = {}

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, v):
        try:
            return validate_extensions(v, cls.___extension_resource_type__.value)
        except Exception as e:
            raise ValueError("Invalid extensions") from e
        return v
