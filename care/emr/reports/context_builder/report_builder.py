# Import all builders to trigger registration
from care.emr.reports.context_builder.builders import (  # noqa: F401
    allergy,
    care_team,
    condition,
    encounter,
    file_upload,
    medication,
    observation,
    patient,
)
from care.emr.reports.context_builder.registry import contex_builder_registry


class ReportContextBuilder:
    """
    Main orchestrator for building report context.
    """

    def __init__(self):
        self.single_builders = contex_builder_registry.get_single_builders()
        self.list_builders = contex_builder_registry.get_queryset_builders()

    def get_full_schema(self):
        schema = {
            "single_objects": {},
            "querysets": {},
        }

        for key, builder_class in self.single_builders.items():
            schema["single_objects"][key] = builder_class.get_schema()

        for key, builder_class in self.list_builders.items():
            schema_data = builder_class.get_schema()
            schema_data["preview_value"] = [
                {field.key: field.preview_value for field in builder_class.fields}
                for _ in range(2)
            ]
            schema["querysets"][key] = schema_data

        return schema

    def build_context(self, ctx: dict, config: dict):
        context = {}

        for single_key, builder_class in self.single_builders.items():
            if single_key in config:
                single_config = config[single_key]
                context[single_key] = builder_class.get_context(
                    ctx=ctx, requested_fields=single_config.get("fields")
                )

        for list_key, builder_class in self.list_builders.items():
            if list_key in config:
                list_config = config[list_key]
                context[list_key] = builder_class.build_list_context(
                    ctx=ctx,
                    filters=list_config.get("filters"),
                    limit=list_config.get("limit"),
                    requested_fields=list_config.get("fields"),
                )

        return context
