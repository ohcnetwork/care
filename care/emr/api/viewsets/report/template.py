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
from care.emr.reports.context_builder import types  # noqa
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
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

    @extend_schema(
        description="Get the complete schema for report template building",
        responses={200: "Success"},
        tags=["template"],
    )
    @action(detail=False, methods=["GET"], url_path="schema")
    def get_schema(self, request, *args, **kwargs):
        return Response({})

    @extend_schema(
        description="Preview a template with sample data",
        request=PreviewTemplateRequest,
        responses={200: "Success"},
        tags=["template"],
    )
    @action(detail=False, methods=["POST"])
    def preview(self, request, *args, **kwargs):
        request_data = PreviewTemplateRequest.model_validate(request.data)

        generator_class = GeneratorRegistry.get(request_data.output_format)
        generator = generator_class()

        context = DataPointRegistry.get(request_data.context)
        preview_context = context(is_preview=True)
        context_dict = {context.context_key: preview_context}

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
            response = HttpResponse(rendered_content, content_type="application/pdf")
            response["Content-Disposition"] = (
                'attachment; filename="template_preview.pdf"'
            )
            return response
        return Response(
            {"error": "Invalid output format"},
            status=status.HTTP_400_BAD_REQUEST,
        )
