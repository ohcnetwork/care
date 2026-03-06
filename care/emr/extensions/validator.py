from pydantic import field_validator

from care.emr.registries.extensions.registry import ExtensionRegistry


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


class ExtensionListRenderer:
    extensions: dict = {}

    @classmethod
    def serialize_extensions(cls, handler, data, obj):
        return handler.deserialize_extensions_list(data, obj)

    @classmethod
    def perform_extra_serialization(cls, mapping, obj, *args, **kwargs):
        if mapping.get("_extensions_rendered"):
            return super().perform_extra_serialization(mapping, obj, *args, **kwargs)
        data = {}
        resource_type = cls.___extension_resource_type__.value
        for key in ExtensionRegistry.get_extensions_for_resource(resource_type):
            extension_handler = ExtensionRegistry.get_extension_obj(resource_type, key)
            current_data = {}
            if key in obj.extensions:
                current_data = obj.extensions[key]
            if extension_handler is None:
                # TODO: Once stable, raise error instead
                data[key] = current_data
            data[key] = cls.serialize_extensions(extension_handler, current_data, obj)

        mapping["extensions"] = data
        mapping["_extensions_rendered"] = True
        return super().perform_extra_serialization(mapping, obj, *args, **kwargs)


class ExtensionRetrieveRenderer(ExtensionListRenderer):
    extensions: dict = {}

    @classmethod
    def serialize_extensions(cls, handler, data, obj):
        return handler.deserialize_extensions_retrieve(data, obj)
