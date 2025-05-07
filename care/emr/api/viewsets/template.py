from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.template import FacilityReportTemplate
from care.emr.registries.report.section import SectionRegistry
from care.emr.reports.discharge_summary import (
    generate_discharge_report_signed_url,
)
from care.emr.resources.template.spec import (
    FacilityReportTemplateCreateSpec,
    FacilityReportTemplateReadSpec,
    FacilityReportTemplateRetrieveSpec,
    FacilityReportTemplateTypes,
    FacilityReportTemplateUpdateSpec,
)
from care.facility.models import Facility


class FacilityReportTemplateViewSet(EMRModelViewSet):
    database_model = FacilityReportTemplate
    pydantic_model = FacilityReportTemplateCreateSpec
    pydantic_read_model = FacilityReportTemplateReadSpec
    pydantic_update_model = FacilityReportTemplateUpdateSpec
    pydantic_retrieve_model = FacilityReportTemplateRetrieveSpec

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_queryset(self):
        return super().get_queryset().filter(facility=self.get_facility_obj())

    def validate_data(self, instance, model_obj=None):
        if (
            model_obj is None
            and FacilityReportTemplate.objects.filter(
                slug=instance.slug, type=instance.type, facility=self.get_facility_obj()
            ).exists()
        ):
            raise ValidationError(
                detail=f"Report template with slug {instance.slug} and type {instance.type} already exists for this facility"
            )

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    @action(detail=False, methods=["GET"])
    def get_available_section_source(self, request, *args, **kwargs):
        return Response(SectionRegistry.all().keys(), status=status.HTTP_200_OK)

    class ReportDisplaySpec(BaseModel):
        render_format: str | None = "typst"
        type: FacilityReportTemplateTypes
        slug: str
        patient_external_id: UUID4 | None = None

    @extend_schema(request=ReportDisplaySpec)
    @action(detail=False, methods=["POST"])
    def display_report(self, request, *args, **kwargs):
        """
        Display the report template for the given facility.
        """
        request_data = self.ReportDisplaySpec(**request.data)

        report_type = request_data.type
        slug = request_data.slug

        if not FacilityReportTemplate.objects.filter(
            slug=slug, type=report_type, facility=self.get_facility_obj()
        ).exists():
            return Response(
                {"detail": "Report template not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if report_type == FacilityReportTemplateTypes.discharge_summary:
            if not request_data.patient_external_id:
                return Response(
                    {
                        "detail": "Patient External ID is required for discharge summary type report."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            report_read_singed_url = generate_discharge_report_signed_url(
                request_data.patient_external_id, request_data.render_format, slug
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
