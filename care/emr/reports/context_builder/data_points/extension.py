import json

from care.emr.registries.extensions.registry import ExtensionRegistry
from care.emr.reports.context_builder.data_points.base import (
    Field,
    QuerysetContextBuilder,
)


class ExtensionValuesBuilder(QuerysetContextBuilder):
    """Iterates over key/value pairs within a single extension's data dict."""

    display = Field(
        display="Extension Field Name",
        preview_value="Related Person",
        mapping=lambda o: o.get("display", ""),
        description="Display name of the extension field",
    )

    value = Field(
        display="Extension Field Value",
        preview_value="John Doe",
        mapping=lambda o: o.get("value", ""),
        description="Value of the extension field",
    )

    def get_context(self):
        data = self.parent_context.get("data", {})
        properties = {}
        write_schema = self.parent_context.get("write_schema", {})
        if isinstance(write_schema, dict):
            properties = write_schema.get("properties", {})

        result = []
        for key, val in data.items():
            display = key
            prop_schema = properties.get(key, {})
            value = None
            if isinstance(prop_schema, dict) and prop_schema.get("title"):
                display = prop_schema["title"]

            if isinstance(val, (dict, list)):
                value = json.dumps(val)
            elif val is not None:
                value = str(val)
            if value:
                result.append({"display": display, "value": value})
        return result


class ExtensionBuilder(QuerysetContextBuilder):
    """
    Generic builder that iterates over a resource's extensions dict.
    """

    __extension_resource_type__ = ""

    name = Field(
        display="Extension Name",
        preview_value="patient_demographics",
        mapping=lambda o: o.get("name", ""),
        description="Name/key of the extension",
    )

    values = Field(
        display="Extension Values",
        preview_value="",
        target_context=ExtensionValuesBuilder,
        description="Key-value pairs within the extension",
    )

    @staticmethod
    def get_write_schema(schema):
        if not schema:
            return {}
        write_schema = schema.get_write_schema()
        if not isinstance(write_schema, dict):
            return {}
        return write_schema

    def get_context(self):
        extensions = getattr(self.parent_context, "extensions", None) or {}
        resource_type = self.__extension_resource_type__
        result = []
        for ext_name, ext_data in extensions.items():
            if not isinstance(ext_data, dict):
                continue
            schema = ExtensionRegistry.get_extension_obj(resource_type, ext_name)
            write_schema = self.get_write_schema(schema)
            result.append(
                {
                    "name": write_schema.get("title", ext_name),
                    "data": ext_data,
                    "schema": schema,
                    "write_schema": write_schema,
                }
            )
        return result


class PatientExtensionBuilder(ExtensionBuilder):
    __extension_resource_type__ = "patient"
