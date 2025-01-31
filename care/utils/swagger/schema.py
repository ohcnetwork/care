from django.core import exceptions as django_exceptions
from drf_spectacular.drainage import warn
from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.plumbing import (
    build_basic_type,
    build_parameter_type,
    follow_model_field_lookup,
    get_view_model,
    resolve_django_path_parameter,
    resolve_regex_path_parameter,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
)
from rest_framework.mixins import ListModelMixin
from rest_framework.schemas.utils import get_pk_description

from care.emr.api.viewsets.base import EMRListMixin


class AutoSchema(SpectacularAutoSchema):
    def get_tags(self):
        if hasattr(self.view, "basename"):
            return [self.view.basename]
        tokenized_path = self._tokenize_path()
        return [tokenized_path[-1]]

    def get_request_serializer(self):
        view = self.view

        action = getattr(view, "action", None)

        if action not in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "list",
            "retrieve",
        ]:
            return None

        if self.method == "POST":
            return getattr(view, "pydantic_model", None)

        if self.method in {"PUT", "PATCH"}:
            return getattr(view, "pydantic_update_model", None) or getattr(
                view, "pydantic_model", None
            )

        return None

    def get_response_serializers(self):
        view = self.view
        action = getattr(view, "action", None)

        if action not in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "list",
            "retrieve",
        ]:
            return None

        if self.method == "DELETE":
            return {"204": {"description": "No response body"}}

        if self.method == "GET":
            if (
                isinstance(self.view, (ListModelMixin, EMRListMixin))
                or self.view.action == "list"
            ):
                model = getattr(view, "pydantic_read_model", None) or getattr(
                    view, "pydantic_model", None
                )
            else:
                model = (
                    getattr(view, "pydantic_retrieve_model", None)
                    or getattr(view, "pydantic_read_model", None)
                    or getattr(view, "pydantic_model", None)
                )

        elif self.method in ["POST", "PUT", "PATCH"]:
            model = getattr(view, "pydantic_read_model", None) or getattr(
                view, "pydantic_model", None
            )
        else:
            return None

        return {200: model} if model else None

    def _resolve_path_parameters(self, variables):
        if hasattr(self.view, "database_model"):
            model = self.view.database_model
        else:
            model = get_view_model(self.view)
        parameters = []
        for variable in variables:
            schema = build_basic_type(OpenApiTypes.STR)
            description = ""

            resolved_parameter = resolve_django_path_parameter(
                self.path_regex,
                variable,
                self.map_renderers("format"),
            )
            if not resolved_parameter:
                resolved_parameter = resolve_regex_path_parameter(
                    self.path_regex, variable
                )

            if resolved_parameter:
                schema = resolved_parameter["schema"]
            elif model is None:
                warn(
                    f'could not derive type of path parameter "{variable}" because it '
                    f"is untyped and obtaining queryset from the viewset failed. "
                    f"Consider adding a type to the path (e.g. <int:{variable}>) or annotating "
                    f'the parameter type with @extend_schema. Defaulting to "string".'
                )
            else:
                try:
                    if getattr(self.view, "lookup_url_kwarg", None) == variable:
                        model_field_name = getattr(self.view, "lookup_field", variable)
                    elif variable.endswith("_pk"):
                        # Django naturally coins foreign keys *_id. improve chances to match a field
                        model_field_name = f"{variable[:-3]}_id"
                    else:
                        model_field_name = variable
                    model_field = follow_model_field_lookup(model, model_field_name)
                    schema = self._map_model_field(model_field, direction=None)
                    if "description" not in schema and model_field.primary_key:
                        description = get_pk_description(model, model_field)
                except django_exceptions.FieldError:
                    warn(
                        f'could not derive type of path parameter "{variable}" because model '
                        f'"{model.__module__}.{model.__name__}" contained no such field. Consider '
                        f'annotating parameter with @extend_schema. Defaulting to "string".'
                    )

            parameters.append(
                build_parameter_type(
                    name=variable,
                    location=OpenApiParameter.PATH,
                    description=description,
                    schema=schema,
                )
            )

        return parameters
