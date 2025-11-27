from care.emr.reports.context_builder.builders import (  # noqa: F401
    allergy,
    condition,
    encounter,
    file_upload,
    medication,
    observation,
    patient,
    service_request,
)
from care.emr.reports.context_builder.registry import context_builder_registry


class ReportContextBuilder:
    def __init__(self):
        self.single_builders = context_builder_registry.get_single_builders()
        self.queryset_builders = context_builder_registry.get_queryset_builders()

    def get_full_schema(self):
        schema = {
            "single_objects": {},
            "querysets": {},
        }

        for key, builder_class in self.single_builders.items():
            schema["single_objects"][key] = builder_class.get_schema()

        for key, builder_class in self.queryset_builders.items():
            schema_data = builder_class.get_schema()
            schema_data["preview_value"] = [
                {field.key: field.preview_value for field in builder_class.fields}
                for _ in range(2)
            ]
            schema["querysets"][key] = schema_data

        return schema

    def build_context(
        self, ctx: dict, config: dict, requested_fields: dict | None = None
    ):
        context = {}
        requested_fields = requested_fields or {}

        for single_key, builder_class in self.single_builders.items():
            if single_key in config:
                fields_to_fetch = requested_fields.get(single_key)
                context[single_key] = builder_class.get_context(
                    ctx=ctx, requested_fields=fields_to_fetch
                )

        for queryset_key, builder_class in self.queryset_builders.items():
            if queryset_key in config:
                queryset_config = config[queryset_key]
                fields_to_fetch = requested_fields.get(queryset_key)
                context[queryset_key] = builder_class.build_list_context(
                    ctx=ctx,
                    filters=queryset_config.get("filters"),
                    limit=queryset_config.get("limit"),
                    requested_fields=fields_to_fetch,
                )

        return context
