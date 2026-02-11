from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.base import Field
from care.emr.reports.context_builder.type_registry import FieldTypeRegistry
from care.emr.reports.renderer.generators.registry import GeneratorRegistry
from care.emr.reports.report_type_registry import ReportTypeRegistry


def _extract_fields_from_context(context_class, visited=None):  # noqa: PLR0912
    if visited is None:
        visited = set()

    class_name = context_class.__name__
    if class_name in visited:
        return []
    visited.add(class_name)

    fields = []
    for attr_name in dir(context_class):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(context_class, attr_name)
            if isinstance(attr, Field):
                field_schema = {
                    "key": attr_name,
                    "display": attr.display,
                    "description": attr.description,
                    "type": attr.type,
                }

                if attr.preview_value is not None:
                    if isinstance(attr.preview_value, (list, dict)):
                        field_schema["preview_value"] = attr.preview_value
                    else:
                        field_schema["preview_value"] = str(attr.preview_value)
                elif attr.preview_fn:
                    try:
                        sample = attr.preview_fn()
                        field_schema["preview_value"] = str(sample)
                    except Exception:
                        field_schema["preview_value"] = ""

                if attr.target_context:
                    field_schema["is_nested_context"] = True
                    field_schema["nested_context_type"] = (
                        attr.target_context.__context_type__
                    )
                    field_schema["nested_context_filters"] = (
                        _extract_filters_from_context(attr.target_context)
                    )
                    nested_fields = _extract_fields_from_context(
                        attr.target_context, visited.copy()
                    )
                    if nested_fields:
                        field_schema["fields"] = nested_fields

                fields.append(field_schema)
        except Exception:  # noqa: S112
            continue

    return sorted(fields, key=lambda f: f["display"])


def _extract_filters_from_context(context_class):
    filters = []
    if hasattr(context_class, "filterset_class") and context_class.filterset_class:
        for _, filter_obj in context_class.filterset_class.base_filters.items():
            filters.append(
                {
                    "field_name": filter_obj.field_name,
                    "lookup_expr": getattr(filter_obj, "lookup_expr", "exact"),
                }
            )

    return filters


def build_schema():
    all_data_points = DataPointRegistry.get_all()
    contexts = {}

    for slug, context_class in all_data_points.items():
        fields = _extract_fields_from_context(context_class)
        contexts[slug] = {
            "slug": slug,
            "display_name": getattr(
                context_class,
                "__display_name__",
                slug.replace("_", " ").title(),
            ),
            "description": getattr(context_class, "__description__", ""),
            "context_type": getattr(context_class, "__context_type__", ""),
            "context_key": getattr(context_class, "context_key", slug),
            "standalone": getattr(context_class, "standalone_context", False),
            "fields": fields,
        }

    output_formats = GeneratorRegistry.get_schema()
    custom_types = FieldTypeRegistry.get_all()
    report_types = ReportTypeRegistry.get_schema()

    return {
        "contexts": contexts,
        "output_formats": output_formats,
        "custom_types": custom_types,
        "report_types": report_types,
    }
