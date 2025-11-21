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
    def validate_against_schema(self):
        builder = ReportContextBuilder()
        schema = builder.get_full_schema()

        raw_data = self.model_dump()
        configured_keys = set(raw_data.keys())

        valid_single_keys = set(schema["single_objects"].keys())
        valid_queryset_keys = set(schema["querysets"].keys())
        all_valid_keys = valid_single_keys | valid_queryset_keys

        invalid_keys = configured_keys - all_valid_keys
        if invalid_keys:
            msg = (
                f"Invalid builder keys: {', '.join(sorted(invalid_keys))}. "
                f"Valid keys are: {', '.join(sorted(all_valid_keys))}"
            )
            raise ValueError(msg)

        for key in configured_keys:
            config_data = raw_data[key]

            if not isinstance(config_data, dict):
                msg = f"Config for '{key}' must be a dictionary"
                raise ValueError(msg)

            if key in valid_single_keys:
                # Single object builders must have empty dict
                if config_data:
                    msg = (
                        f"Single object builder '{key}' must have empty config {{}}. "
                        f"Got: {config_data}"
                    )
                    raise ValueError(msg)

            elif key in valid_queryset_keys:
                # Queryset builders can only have 'filters' and 'limit'
                allowed_keys = {"filters", "limit"}
                invalid_config_keys = set(config_data.keys()) - allowed_keys
                if invalid_config_keys:
                    msg = (
                        f"Invalid config keys for queryset builder '{key}': {', '.join(sorted(invalid_config_keys))}. "
                        f"Only 'filters' and 'limit' are allowed."
                    )
                    raise ValueError(msg)

                # Validate the config using QuerysetConfigSpec
                try:
                    QuerysetConfigSpec.model_validate(config_data)
                except Exception as e:
                    msg = f"Invalid config for '{key}': {e!s}"
                    raise ValueError(msg) from e

                # Validate filters against allowed_filters
                if "filters" in config_data:
                    allowed_filters = schema["querysets"][key].get(
                        "allowed_filters", []
                    )
                    for filter_key in config_data["filters"]:
                        base_filter_key = filter_key.split("__")[0]
                        if allowed_filters and base_filter_key not in allowed_filters:
                            msg = (
                                f"Invalid filter '{filter_key}' for '{key}'. "
                                f"Allowed filters are: {', '.join(sorted(allowed_filters))}"
                            )
                            raise ValueError(msg)

        if not configured_keys:
            raise ValueError(
                "context_config must include at least one model configuration"
            )

        return self
