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
        return self.parent_context.get("values", [])


class ExtensionBuilder(QuerysetContextBuilder):
    """
    Generic builder that iterates over a resource's extensions dict.
    """

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

    def get_context(self):
        results = []
        extensions = self.parent_context.extensions
        for name, fields in extensions.items():
            values = [{"display": key, "value": val} for key, val in fields.items()]
            results.append({"name": name, "values": values})
        return results
