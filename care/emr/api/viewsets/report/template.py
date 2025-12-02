import logging

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
from care.emr.reports.context_builder import Field, types  # noqa
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.type_registry import FieldTypeRegistry
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.emr.resources.report.template.spec import (
    TemplateCreateSpec,
    TemplateReadSpec,
    TemplateRetrieveSpec,
    TemplateUpdateSpec,
)
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class TemplateFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template_type = CharFilter(field_name="template_type", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    facility = CharFilter(field_name="facility__external_id", lookup_expr="exact")


class PreviewTemplateRequest(BaseModel):
    template_data: str
    output_format: str = "html"
    context: str


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

    def _extract_fields_from_context(self, context_class, visited=None):  # noqa: PLR0912
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
                        nested_fields = self._extract_fields_from_context(
                            attr.target_context, visited.copy()
                        )
                        if nested_fields:
                            field_schema["fields"] = nested_fields

                    fields.append(field_schema)
            except Exception:  # noqa: S112
                continue

        return fields

    @extend_schema(responses={200: "Success"}, tags=["template"])
    @action(detail=False, methods=["GET"], url_path="schema")
    def get_schema(self, request, *args, **kwargs):
        try:
            all_data_points = DataPointRegistry.get_all()
            contexts = {}

            for slug, context_class in all_data_points.items():
                fields = self._extract_fields_from_context(context_class)
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

            schema = {
                "contexts": contexts,
                "output_formats": output_formats,
                "custom_types": custom_types,
            }

            return Response(schema)

        except Exception as e:
            logger.exception("Failed to generate schema: %s", e)
            return Response(
                {"error": "Failed to generate schema", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=PreviewTemplateRequest, responses={200: "Success"}, tags=["template"]
    )
    @action(detail=False, methods=["POST"])
    def preview(self, request, *args, **kwargs):  # noqa: PLR0911
        try:
            request_data = PreviewTemplateRequest.model_validate(request.data)
        except Exception as e:
            logger.exception("Invalid request data for template preview: %s", e)
            return Response(
                {"error": f"Invalid request data: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not GeneratorRegistry.is_registered(request_data.output_format):
            available_formats = GeneratorRegistry.get_all_formats()
            return Response(
                {
                    "error": f"Invalid output format '{request_data.output_format}'",
                    "available_formats": available_formats,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not DataPointRegistry.is_registered(request_data.context):
            available_contexts = list(DataPointRegistry.get_all().keys())
            return Response(
                {
                    "error": f"Invalid context '{request_data.context}'",
                    "available_contexts": available_contexts,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generator_class = GeneratorRegistry.get(request_data.output_format)
            generator = generator_class()

            context_class = DataPointRegistry.get(request_data.context)
            preview_context = context_class(is_preview=True)
            context_dict = {context_class.context_key: preview_context}

            rendered_content = Renderer(generator).render(
                request_data.template_data, context_dict
            )

            if request_data.output_format == "html":
                return Response(
                    rendered_content,
                    content_type="text/html",
                    status=status.HTTP_200_OK,
                )
            if request_data.output_format == "pdf":
                response = HttpResponse(
                    rendered_content, content_type="application/pdf"
                )
                response["Content-Disposition"] = (
                    'attachment; filename="template_preview.pdf"'
                )
                return response

            format_config = GeneratorRegistry.get_format_config(
                request_data.output_format
            )
            response = HttpResponse(
                rendered_content, content_type=format_config["mime_type"]
            )
            response["Content-Disposition"] = (
                f'attachment; filename="preview{format_config["file_extension"]}"'
            )
            return response

        except Exception as e:
            logger.exception("Preview generation failed: %s", e)
            return Response(
                {
                    "error": "Failed to generate preview",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
