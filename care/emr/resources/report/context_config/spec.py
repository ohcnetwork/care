from difflib import get_close_matches

from pydantic import BaseModel, field_validator, model_validator

from care.emr.reports.context_builder.report_builder import ReportContextBuilder


class QuerysetConfigSpec(BaseModel):
    filters: dict = {}
    limit: int | None = None

    @field_validator("limit")
    @classmethod
    def validate_limit_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("limit must be a positive integer")
        return v


class ContextConfigSpec(BaseModel):
    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_against_schema(self):  # noqa PLR0912
        builder = ReportContextBuilder()
        schema = builder.get_full_schema()

        raw_data = self.model_dump()
        configured_keys = set(raw_data.keys())

        valid_single_keys = set(schema["single_objects"].keys())
        valid_queryset_keys = set(schema["querysets"].keys())
        all_valid_keys = valid_single_keys | valid_queryset_keys

        invalid_keys = configured_keys - all_valid_keys
        if invalid_keys:
            error_parts = []
            for invalid_key in sorted(invalid_keys):
                suggestions = get_close_matches(
                    invalid_key, all_valid_keys, n=3, cutoff=0.6
                )
                if suggestions:
                    error_parts.append(
                        f"'{invalid_key}' (did you mean: {', '.join(suggestions)}?)"
                    )
                else:
                    error_parts.append(f"'{invalid_key}'")

            invalid_list = ", ".join(error_parts)
            valid_list = ", ".join(sorted(all_valid_keys))
            msg = f"Invalid builder key(s): {invalid_list}. Available builders: {valid_list}"
            raise ValueError(msg)

        for key in configured_keys:
            config_data = raw_data[key]

            if not isinstance(config_data, dict):
                msg = f"Config for '{key}' must be a dictionary"
                raise ValueError(msg)

            if key in valid_single_keys:
                if config_data:
                    msg = f"Builder '{key}' is a single object and must have empty config {{}}, got: {config_data}"
                    raise ValueError(msg)

            elif key in valid_queryset_keys:
                allowed_keys = {"filters", "limit"}
                invalid_config_keys = set(config_data.keys()) - allowed_keys
                if invalid_config_keys:
                    invalid_str = ", ".join(
                        f"'{k}'" for k in sorted(invalid_config_keys)
                    )
                    msg = f"Invalid config keys for '{key}': {invalid_str}. Only 'filters' and 'limit' allowed"
                    raise ValueError(msg)

                try:
                    QuerysetConfigSpec.model_validate(config_data)
                except Exception as e:
                    err = f"Invalid config for '{key}'"
                    raise ValueError(err) from e

                if "filters" in config_data:
                    allowed_filters = schema["querysets"][key].get(
                        "allowed_filters", []
                    )
                    for filter_key in config_data["filters"]:
                        base_filter_key = filter_key.split("__")[0]
                        if allowed_filters and base_filter_key not in allowed_filters:
                            allowed_str = ", ".join(sorted(allowed_filters))
                            msg = f"Invalid filter '{filter_key}' for '{key}'. Allowed: {allowed_str}"
                            raise ValueError(msg)

        if not configured_keys:
            raise ValueError("context_config must include at least one builder")

        return self
