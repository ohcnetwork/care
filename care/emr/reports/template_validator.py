from care.emr.reports.context_builder.report_builder import ReportContextBuilder
from care.emr.reports.renderer.template_engine import TemplateEngine


def get_referenced_builders(template_data: str) -> set[str]:
    template_engine = TemplateEngine()
    builder = ReportContextBuilder()

    variables = template_engine.extract_variables(template_data)
    all_builders = set(builder.single_builders.keys()) | set(
        builder.list_builders.keys()
    )

    referenced_builders = set()
    for var in variables:
        if var in ["loop", "current_date", "current_datetime", "current_time"]:
            continue

        parts = var.split(".")
        if parts:
            builder_key = parts[0]
            if builder_key in all_builders:
                referenced_builders.add(builder_key)

    return referenced_builders


def validate_template_fields(template_data: str) -> tuple[bool, str | None]:
    template_engine = TemplateEngine()
    builder = ReportContextBuilder()

    variables = template_engine.extract_variables(template_data)

    if not variables:
        return True, None

    schema = builder.get_full_schema()
    available_fields = {}

    for builder_key, builder_schema in schema["single_objects"].items():
        available_fields[builder_key] = {
            field["key"] for field in builder_schema["fields"]
        }

    for builder_key, builder_schema in schema["querysets"].items():
        available_fields[builder_key] = {
            field["key"] for field in builder_schema["fields"]
        }

    invalid_refs = []
    for var in variables:
        if var in ["loop", "current_date", "current_datetime", "current_time"]:
            continue

        parts = var.split(".")
        if len(parts) < 2:  # noqa: PLR2004
            continue

        builder_key = parts[0]

        if builder_key not in available_fields:
            continue

        field_key = (
            parts[1]
            if len(parts) >= 2 and not parts[1].isdigit()  # noqa: PLR2004
            else (parts[2] if len(parts) >= 3 else None)  # noqa: PLR2004
        )

        if field_key and field_key not in available_fields[builder_key]:
            available = ", ".join(sorted(available_fields[builder_key]))
            invalid_refs.append(
                f"{var} (field '{field_key}' not found in '{builder_key}'. "
                f"Available fields: {available})"
            )

    if invalid_refs:
        error_msg = "Invalid field references in template:\n  - " + "\n  - ".join(
            invalid_refs
        )
        return False, error_msg

    return True, None


def validate_context_config_completeness(
    template_data: str, context_config: dict
) -> tuple[bool, str | None]:
    referenced_builders = get_referenced_builders(template_data)
    context_builders = set(context_config.keys()) if context_config else set()
    missing_builders = referenced_builders - context_builders

    if missing_builders:
        error_msg = (
            f"Template references builders that are not in context_config: {', '.join(sorted(missing_builders))}. "
            f"Please add these to context_config."
        )
        return False, error_msg

    return True, None


def is_builder_referenced(template_data: str, builder_key: str) -> bool:
    referenced_builders = get_referenced_builders(template_data)
    return builder_key in referenced_builders
