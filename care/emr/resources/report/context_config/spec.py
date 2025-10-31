from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from care.emr.reports.context_builder.report_builder import ReportContextBuilder


class FieldsConfigSpec(BaseModel):
    fields: list[str]

    @field_validator("fields")
    @classmethod
    def validate_fields_not_empty(cls, v):
        if not v:
            raise ValueError("fields list cannot be empty")
        return v


class QuerysetConfigSpec(BaseModel):
    fields: list[str]
    filters: dict = {}
    limit: int | None = None

    @field_validator("fields")
    @classmethod
    def validate_fields_not_empty(cls, v):
        if not v:
            raise ValueError("fields list cannot be empty")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("limit must be a positive integer")
        return v


class ContextConfigSpec(BaseModel):
    """
    Dynamic context config that supports any registered builder.
    Uses __root__ to accept any dict structure, then validates against schema.
    """

    model_config = {"extra": "allow"}

    # Accept any additional fields dynamically
    def __init__(self, **data: Any):
        super().__init__(**data)
        # Store the raw data for validation
        self._raw_data = data

    @model_validator(mode="after")
    def validate_against_schema(self):
        """Validate all configured builders against the dynamic schema"""
        builder = ReportContextBuilder()
        schema = builder.get_full_schema()

        # Get all configured keys from the raw data
        configured_keys = set(self._raw_data.keys())

        # Get all valid keys from schema
        valid_single_keys = set(schema["single_objects"].keys())
        valid_queryset_keys = set(schema["querysets"].keys())
        all_valid_keys = valid_single_keys | valid_queryset_keys

        # Check for invalid keys
        invalid_keys = configured_keys - all_valid_keys
        if invalid_keys:
            msg = (
                f"Invalid builder keys: {', '.join(sorted(invalid_keys))}. "
                f"Valid keys are: {', '.join(sorted(all_valid_keys))}"
            )
            raise ValueError(msg)

        # Validate each configured builder
        for key in configured_keys:
            config_data = self._raw_data[key]

            # Determine if it's a single object or queryset
            if key in valid_single_keys:
                # Validate as FieldsConfigSpec
                try:
                    config = FieldsConfigSpec.model_validate(config_data)
                except Exception as e:
                    msg = f"Invalid config for '{key}': {e!s}"
                    raise ValueError(msg) from e

                # Validate field names
                valid_fields = {
                    field["key"] for field in schema["single_objects"][key]["fields"]
                }
                for field_name in config.fields:
                    if field_name not in valid_fields:
                        msg = (
                            f"Invalid field '{field_name}' for {key}. "
                            f"Valid fields are: {', '.join(sorted(valid_fields))}"
                        )
                        raise ValueError(msg)

            elif key in valid_queryset_keys:
                # Validate as QuerysetConfigSpec
                try:
                    config = QuerysetConfigSpec.model_validate(config_data)
                except Exception as e:
                    msg = f"Invalid config for '{key}': {e!s}"
                    raise ValueError(msg) from e

                # Validate field names
                valid_fields = {
                    field["key"] for field in schema["querysets"][key]["fields"]
                }
                for field_name in config.fields:
                    if field_name not in valid_fields:
                        msg = (
                            f"Invalid field '{field_name}' for {key}. "
                            f"Valid fields are: {', '.join(sorted(valid_fields))}"
                        )
                        raise ValueError(msg)

        # Ensure at least one builder is configured
        if not configured_keys:
            raise ValueError(
                "context_config must include at least one model configuration"
            )

        return self
