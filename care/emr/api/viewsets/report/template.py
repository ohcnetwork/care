import re

from django.http import HttpResponse
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class TemplateFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template_type = CharFilter(field_name="template_type", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    facility = CharFilter(field_name="facility__external_id", lookup_expr="exact")


class PreviewTemplateRequest(BaseModel):
    template_data: str
    output_format: str = "html"
    options: dict = {}


class TemplateViewSet(EMRModelViewSet):
    lookup_field = "slug"
    database_model = Template
    pydantic_model = TemplateCreateSpec
    pydantic_read_model = TemplateReadSpec
    pydantic_update_model = TemplateUpdateSpec
    pydantic_retrieve_model = TemplateRetrieveSpec

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TemplateFilters
    ordering_fields = ["created_date", "name", "template_type"]

    def recalculate_slug(self, instance):
        if instance.facility:
            instance.slug = Template.calculate_slug_from_facility(
                instance.facility.external_id, instance.slug
            )
        else:
            instance.slug = Template.calculate_slug_from_instance(instance.slug)

    def perform_create(self, instance):
        self.recalculate_slug(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        self.recalculate_slug(instance)
        return super().perform_update(instance)

    def validate_data(self, instance, model_obj=None):
        queryset = Template.objects.all()
        facility = None
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)
            facility = (
                str(model_obj.facility.external_id) if model_obj.facility else None
            )
        else:
            facility = instance.facility

        if facility:
            slug = Template.calculate_slug_from_facility(facility, instance.slug_value)
        else:
            slug = Template.calculate_slug_from_instance(instance.slug_value)

        queryset = queryset.filter(slug__iexact=slug)
        if queryset.exists():
            raise ValidationError("Slug already exists.")

        return super().validate_data(instance, model_obj)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and "facility" in self.request.GET:
            facility = get_object_or_404(
                Facility, external_id=self.request.GET["facility"]
            )

            queryset = queryset.filter(facility=facility)
        elif self.action == "list" and "facility" not in self.request.GET:
            queryset = queryset.filter(facility__isnull=True)
        return queryset

    @extend_schema(
        description="Get the complete schema for report template building",
        responses={200: "Success"},
        tags=["template"],
    )
    @action(detail=False, methods=["GET"], url_path="schema")
    def get_schema(self, request, *args, **kwargs):
        try:
            from care.emr.reports.context_builder import types  # noqa
            from care.emr.reports.context_builder.type_registry import FieldTypeRegistry

            builder = ReportContextBuilder()
            schema = builder.get_full_schema()

            # Add registered type definitions
            schema["types"] = FieldTypeRegistry.get_all()

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
    def preview(self, request, *args, **kwargs):  # noqa: PLR0911, PLR0912
        try:
            preview_request = PreviewTemplateRequest.model_validate(request.data)
        except Exception as e:
            return Response(
                {"error": f"Invalid request data: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_data = preview_request.template_data
        output_format = preview_request.output_format.lower()
        options = preview_request.options

        try:
            template_engine = TemplateEngine()

            extracted_vars = template_engine.extract_variables(template_data)
            context_builder = ReportContextBuilder()
            schema = context_builder.get_full_schema()

            def is_builder_referenced(builder_key):
                for var in extracted_vars:
                    if var in [
                        "loop",
                        "current_date",
                        "current_datetime",
                        "current_time",
                    ]:
                        continue
                    parts = var.split(".")
                    if parts and parts[0] == builder_key:
                        return True
                return False

            preview_context = {}

            for obj_key in schema["single_objects"]:
                if is_builder_referenced(obj_key):
                    preview_context[obj_key] = {}
                    builder_schema = schema["single_objects"][obj_key]
                    for field in builder_schema.get("fields", []):
                        preview_context[obj_key][field["key"]] = field["preview_value"]

            for qs_key in schema["querysets"]:
                if is_builder_referenced(qs_key):
                    qs_data = schema["querysets"][qs_key]
                    preview_context[qs_key] = qs_data.get("preview_value", [])

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

            validation_result = {
                "syntax_valid": valid,
                "syntax_error": error if not valid else None,
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
