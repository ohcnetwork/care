from django.db import models
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import Patient
from care.emr.models.template import ReportTemplate
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.discharge_summary import (
    generate_discharge_report_signed_url,
)
from care.emr.reports.renderer.dummy import DummyRenderer
from care.emr.resources.template.spec import (
    ReportTemplateCreateSpec,
    ReportTemplateReadSpec,
    ReportTemplateRetrieveSpec,
    ReportTemplateTypes,
    ReportTemplateUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController


class TemplateFilterSet(filters.FilterSet):
    slug = filters.CharFilter(field_name="slug", lookup_expr="icontains")
    type = filters.CharFilter(field_name="type", lookup_expr="icontains")


class ReportTemplateViewSet(EMRModelViewSet):
    database_model = ReportTemplate
    pydantic_model = ReportTemplateCreateSpec
    pydantic_read_model = ReportTemplateReadSpec
    pydantic_update_model = ReportTemplateUpdateSpec
    pydantic_retrieve_model = ReportTemplateRetrieveSpec
    filterset_class = TemplateFilterSet
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_list_template_in_facility",
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to access this endpoint")

        queryset = ReportTemplate.objects.all()

        if self.lookup_field not in self.kwargs:
            if self.request.query_params.get("facility"):
                facility = self.request.query_params.get("facility")
                queryset = queryset.filter(
                    models.Q(facility__external_id=facility) | models.Q(facility=None)
                )
            else:
                queryset = queryset.filter(facility=None)
        return queryset

    def validate_data(self, instance, model_obj=None):
        if (
            model_obj is None
            and ReportTemplate.objects.filter(
                slug=instance.slug, facility__external_id=instance.facility
            ).exists()
        ):
            raise ValidationError(
                detail=f"Report template with slug {instance.slug} already exists for this facility/instance"
            )

    def authorize_create(self, instance):
        if instance.facility is None:
            if not AuthorizationController.call(
                "can_write_template_in_instance", self.request.user
            ):
                raise PermissionDenied(
                    "You do not have permission to create template for facility"
                )
        elif not AuthorizationController.call(
            "can_write_template_in_facility", self.request.user, instance.facility
        ):
            raise PermissionDenied(
                "You do not have permission to create template for facility"
            )

    def authorize_destroy(self, instance):
        if instance.facility is None:
            if not AuthorizationController.call(
                "can_write_template_in_instance", self.request.user
            ):
                raise PermissionDenied(
                    "You do not have permission to create template for facility"
                )
        elif not AuthorizationController.call(
            "can_write_template_in_facility", self.request.user, instance.facility
        ):
            raise PermissionDenied(
                "You do not have permission to create template for facility"
            )

    def authorize_update(self, instance, model_obj=None):
        if model_obj:
            if model_obj.facility is None:
                if not AuthorizationController.call(
                    "can_write_template_in_instance", self.request.user
                ):
                    raise PermissionDenied(
                        "You do not have permission to create template for facility"
                    )
            elif not AuthorizationController.call(
                "can_write_template_in_facility", self.request.user, instance.facility
            ):
                raise PermissionDenied(
                    "You do not have permission to create template for facility"
                )

    @action(detail=False, methods=["GET"])
    def get_available_section_source(self, request, *args, **kwargs):
        if not AuthorizationController.call(
            "can_list_template_in_facility",
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to access this endpoint")

        output = {
            key: section_cls(
                config={}, context={}, renderer=DummyRenderer()
            ).available_fields()
            for key, section_cls in SectionRegistry.all().items()
        }
        return Response(output, status=status.HTTP_200_OK)

    class ReportDisplaySpec(BaseModel):
        render_format: str | None = "typst"
        type: ReportTemplateTypes
        slug: str
        patient_external_id: UUID4 | None = None
        facility: UUID4 | None = None

    @extend_schema(request=ReportDisplaySpec)
    @action(detail=False, methods=["POST"])
    def display_report(self, request, *args, **kwargs):
        """
        Display the report template for the given facility.
        """

        if not AuthorizationController.call(
            "can_list_template_in_facility",
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to access this endpoint")

        request_data = self.ReportDisplaySpec(**request.data)

        report_type = request_data.type
        slug = request_data.slug
        facility = request_data.facility

        if facility:
            facility = get_object_or_404(Facility, external_id=facility)

        if not ReportTemplate.objects.filter(
            slug=slug, type=report_type, facility=facility
        ).exists():
            return Response(
                {"detail": "Report template not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if report_type == ReportTemplateTypes.discharge_summary:
            if not request_data.patient_external_id:
                return Response(
                    {
                        "detail": "Patient External ID is required for discharge summary type report."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            get_object_or_404(Patient, external_id=request_data.patient_external_id)
            report_read_singed_url = generate_discharge_report_signed_url(
                request_data.patient_external_id,
                request_data.facility,
                request_data.render_format,
                slug,
            )
            return Response(
                {"report_read_signed_url": report_read_singed_url},
                status=status.HTTP_200_OK,
            )
        # TODO: Handle other report types when added
        return Response(
            {"detail": "Report template not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
