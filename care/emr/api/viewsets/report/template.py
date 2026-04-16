import logging

from django.conf import settings
from django.db.models import Q
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.report.template import Template
from care.emr.reports.context_builder import (  # noqa
    Field,
    SingleUserIdContextBuilder,
    types,
)
from care.emr.reports.context_builder.data_point_registry import DataPointRegistry
from care.emr.reports.context_builder.data_points.utils import build_schema
from care.emr.reports.renderer.generators import GeneratorRegistry
from care.emr.reports.renderer.renderer import Renderer
from care.emr.resources.report.template.spec import (
    TemplateCreateSpec,
    TemplateReadSpec,
    TemplateRetrieveSpec,
    TemplateUpdateSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyBooleanFilter
from care.utils.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class TemplateFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    template_type = CharFilter(field_name="template_type", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    facility = CharFilter(field_name="facility__external_id", lookup_expr="exact")
    facility_only = DummyBooleanFilter()


class PreviewTemplateRequest(BaseModel):
    template_data: str
    output_format: str = "html"
    context: str
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

    def authorize_retrieve(self, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_list_facility_template", self.request.user, model_instance.facility
        ):
            raise PermissionDenied("You do not have permission to read templates")

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_write_facility_template", self.request.user, model_instance.facility
        ):
            raise PermissionDenied("You do not have permission to write templates")
        if not model_instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("You do not have permission to write templates")

    def authorize_create(self, instance):
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_template", self.request.user, facility
            ):
                raise PermissionDenied("You do not have permission to write templates")
        if not instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("You do not have permission to write templates")

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
        if self.action == "list":
            if "facility" in self.request.GET:
                facility = get_object_or_404(
                    Facility, external_id=self.request.GET["facility"]
                )
                if not AuthorizationController.call(
                    "can_list_facility_template", self.request.user, facility
                ):
                    raise PermissionDenied(
                        "You do not have permission to read templates"
                    )
                if self.request.GET.get("facility_only", "false").lower() == "true":
                    queryset = queryset.filter(facility=facility)
                else:
                    queryset = queryset.filter(
                        Q(facility=facility) | Q(facility__isnull=True)
                    )
            else:
                queryset = queryset.filter(facility__isnull=True)
        return queryset

    @extend_schema(responses={200: "Success"}, tags=["template"])
    @action(detail=False, methods=["GET"], url_path="schema")
    def get_schema(self, request, *args, **kwargs):
        if not AuthorizationController.call("can_view_template_schema", request.user):
            raise PermissionDenied(
                "You do not have permission to access template schema"
            )
        try:
            return Response(build_schema())
        except Exception as e:
            logger.exception("Failed to generate schema: %s", e)
            return Response(
                {"error": "Failed to generate schema"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=PreviewTemplateRequest, responses={200: "Success"}, tags=["template"]
    )
    @action(detail=False, methods=["POST"])
    def preview(self, request, *args, **kwargs):
        AuthorizationController.call("can_preview_template", request.user)

        request_data = PreviewTemplateRequest.model_validate(request.data)

        if not GeneratorRegistry.is_registered(request_data.output_format):
            raise ValidationError("Invalid output format")

        if not DataPointRegistry.is_registered(request_data.context):
            raise ValidationError("Invalid context")

        try:
            generator_class = GeneratorRegistry.get(request_data.output_format)
            generator = generator_class()

            options_model = generator_class.options_model
            validated_options = options_model.model_validate(request_data.options)

            context_class = DataPointRegistry.get(request_data.context)
            preview_context = context_class(is_preview=True)
            context_dict = {context_class.context_key: preview_context}

            context_dict["current_user"] = SingleUserIdContextBuilder(
                context=request.user,
            )

            rendered_content = Renderer(generator).render(
                request_data.template_data, context_dict, validated_options
            )

            return generator.get_http_response(rendered_content)

        except Exception as e:
            if settings.DEBUG:
                raise e
            raise ValidationError("Preview generation failed") from e
