import json
from enum import Enum
from os import getenv

from django.conf import settings
from django.core.exceptions import FieldError
from django_filters.constants import EMPTY_VALUES
from rest_framework.exceptions import ValidationError


class OTPResourceType(str, Enum):
    diagnostic_report = "diagnostic_report"
    medication_request_prescription = "medication_request_prescription"


class QuerysetEnablerMixin:
    """
    Mixin to enable queryset filtering based on the presence of a filterset_class attribute.
    """

    resource_type = OTPResourceType

    def config_key(self):
        return f"OTP_{self.resource_type.value.upper()}_FILTERS"

    def get_env_value(self, key):
        if not getenv(key):
            return {}
        try:
            return json.loads(getenv(key))
        except json.JSONDecodeError as e:
            raise ValidationError(
                {key: "Invalid JSON in default filter configuration."}
            ) from e

    def get_read_filters(self):
        return self.get_env_value(self.config_key())

    def apply_default_filters(self, queryset):
        read_filters = self.get_read_filters()
        if not read_filters:
            return queryset.none()
        query_params = self.request.query_params
        allowed_filters = set(getattr(self.filterset_class, "base_filters", {}))
        for filter_config in read_filters:
            filter_name = filter_config.get("name")
            properties = filter_config.get("properties", {})
            if not filter_name or filter_name in query_params:
                continue
            if filter_name not in allowed_filters:
                raise ValidationError({filter_name: "Invalid filter"})
            value = properties.get("value")
            if value in EMPTY_VALUES:
                continue

            field_name = properties.get("field_name", filter_name)
            lookup_expr = properties.get("lookup_expr", "exact")
            try:
                queryset = queryset.filter(**{f"{field_name}__{lookup_expr}": value})
            except FieldError as e:
                raise ValidationError(
                    {filter_name: "Invalid default filter configuration"}
                ) from e
        return queryset

    def get_queryset(self):
        if not settings.OTP_QUERYSET_ENABLED:
            return self.database_model.objects.none()
        queryset = super().get_queryset()
        if self.action == "list":
            return self.apply_default_filters(queryset)
        return queryset
