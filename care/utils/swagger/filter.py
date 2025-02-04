from django.db import models
from drf_spectacular.contrib.django_filters import DjangoFilterExtension
from drf_spectacular.drainage import add_trace_message
from drf_spectacular.plumbing import build_basic_type, get_manager, get_view_model
from drf_spectacular.types import OpenApiTypes


class CustomFilterExtension(DjangoFilterExtension):
    target_class = "django_filters.rest_framework.DjangoFilterBackend"
    priority = 1

    def _get_schema_from_model_field(self, auto_schema, filter_field, model):
        model_field = self._get_model_field(filter_field, model)

        if self._is_gis(model_field):
            return build_basic_type(OpenApiTypes.STR)

        if not isinstance(model_field, models.Field):
            if hasattr(auto_schema.view, "database_model"):
                qs = auto_schema.view.database_model.objects.all()
            else:
                qs = auto_schema.view.get_queryset()
            model_field = qs.query.annotations[filter_field.field_name].field
        return auto_schema._map_model_field(model_field, direction=None)  # noqa SLF001

    def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
        if hasattr(auto_schema.view, "database_model"):
            model = auto_schema.view.database_model
        else:
            model = get_view_model(auto_schema.view)
        if not model:
            return []

        filterset_class = self.target.get_filterset_class(
            auto_schema.view, get_manager(model).none()
        )
        if not filterset_class:
            return []

        result = []
        with add_trace_message(filterset_class):
            for field_name, filter_field in filterset_class.base_filters.items():
                result += self.resolve_filter_field(
                    auto_schema, model, filterset_class, field_name, filter_field
                )
        return result
