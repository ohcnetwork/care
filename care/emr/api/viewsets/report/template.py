import re

from django.http import HttpResponse
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.report.template import Template
from care.emr.reports.context_builder.report_builder import ReportContextBuilder
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.emr.reports.renderer.template_engine import TemplateEngine
from care.emr.resources.report.template.spec import (
    TemplateCreateSpec,
    TemplateReadSpec,
    TemplateRetrieveSpec,
    TemplateUpdateSpec,
)


class TemplateFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template_type = CharFilter(field_name="template_type", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    facility = CharFilter(field_name="facility__external_id", lookup_expr="exact")


class PreviewTemplateRequest(BaseModel):
    template_data: str
    context_config: dict = {}
    output_format: str = "html"
    options: dict = {}


class TemplateViewSet(EMRModelViewSet):
    database_model = Template
    pydantic_model = TemplateCreateSpec
    pydantic_read_model = TemplateReadSpec
    pydantic_update_model = TemplateUpdateSpec
    pydantic_retrieve_model = TemplateRetrieveSpec

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TemplateFilters
    ordering_fields = ["created_date", "name", "template_type"]

    @extend_schema(
        description="Get the complete schema for report template building",
        responses={200: "Success"},
        tags=["template"],
    )
    @action(detail=False, methods=["GET"], url_path="schema")
    def get_schema(self, request, *args, **kwargs):
        try:
            builder = ReportContextBuilder()
            schema = builder.get_full_schema()
            return Response(schema)

        except Exception as e:
            return Response(
                {"error": f"Failed to generate schema: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        description="Preview a template with sample data",
        request=PreviewTemplateRequest,
        responses={200: "Success"},
        tags=["template"],
    )
    @action(detail=False, methods=["POST"])
    def preview(self, request, *args, **kwargs):  # noqa: PLR0911, PLR0912, PLR0915
        try:
            preview_request = PreviewTemplateRequest.model_validate(request.data)
        except Exception as e:
            return Response(
                {"error": f"Invalid request data: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_data = preview_request.template_data
        context_config = preview_request.context_config
        output_format = preview_request.output_format.lower()
        options = preview_request.options

        try:
            context_builder = ReportContextBuilder()
            schema = context_builder.get_full_schema()

            preview_context = {}

            for obj_key in ["patient", "encounter"]:
                if obj_key in context_config:
                    requested_fields = context_config[obj_key].get("fields", [])
                    if requested_fields:
                        preview_context[obj_key] = {}
                        builder_schema = schema["single_objects"].get(obj_key, {})
                        for field in builder_schema.get("fields", []):
                            if field["key"] in requested_fields:
                                preview_context[obj_key][field["key"]] = field[
                                    "preview_value"
                                ]

            for qs_key, qs_data in schema.get("querysets", {}).items():
                if qs_key in context_config:
                    requested_fields = context_config[qs_key].get("fields", [])
                    if requested_fields:
                        preview_items = qs_data.get("preview_value", [])

                        filtered_items = []
                        for item in preview_items:
                            filtered_item = {
                                k: v for k, v in item.items() if k in requested_fields
                            }
                            filtered_items.append(filtered_item)

                        preview_context[qs_key] = filtered_items

            template_engine = TemplateEngine()

            try:
                generator_class = GeneratorRegistry.get(output_format)
                generator = generator_class()
            except KeyError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            renderer = Renderer(template_engine, generator)

            valid, error = renderer.validate_syntax(template_data)
            extracted_vars = renderer.extract_variables(template_data)

            validation_result = {
                "syntax_valid": valid,
                "syntax_error": error if not valid else None,
                "variables": list(extracted_vars),
            }

            if not valid:
                return Response(
                    {
                        "error": f"Template validation failed: {error}",
                        "validation": validation_result,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                output_bytes = renderer.render(template_data, preview_context, options)
                validation_result["render_valid"] = True
                validation_result["render_error"] = None

            except Exception as e:
                validation_result["render_valid"] = False
                error_message = str(e)

                if "has no attribute" in error_message:
                    match = re.search(r"has no attribute '(\w+)'", error_message)
                    if match:
                        field_name = match.group(1)
                        error_message = f"Field '{field_name}' does not exist or is not available in the context. Please check your template for typos or ensure this field is included in your context configuration."

                validation_result["render_error"] = error_message
                return Response(
                    {
                        "error": error_message,
                        "validation": validation_result,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if output_format == "html":
                return Response(
                    {
                        "html": output_bytes.decode("utf-8"),
                        "validation": validation_result,
                    }
                )
            response = HttpResponse(output_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                'attachment; filename="template_preview.pdf"'
            )
            return response

        except Exception as e:
            return Response(
                {"error": f"Preview generation failed: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
