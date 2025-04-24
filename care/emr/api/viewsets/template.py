from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.registries.report_section.report_section import SectionRegistry
from care.emr.resources.template.spec import (
    FacilityReportTemplateCreateSpec,
    FacilityReportTemplateReadSpec,
    FacilityReportTemplateRetrieveSpec,
    FacilityReportTemplateUpdateSpec,
)
from care.facility.models import Facility, FacilityReportTemplate


class FacilityReportTemplateViewSet(EMRModelViewSet):
    database_model = FacilityReportTemplate
    pydantic_model = FacilityReportTemplateCreateSpec
    pydantic_read_model = FacilityReportTemplateReadSpec
    pydantic_update_model = FacilityReportTemplateUpdateSpec
    pydantic_retrieve_model = FacilityReportTemplateRetrieveSpec

    def permissions_controller(self, request):
        return request.user.is_superuser

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_queryset(self):
        return super().get_queryset().filter(facility=self.get_facility_obj())

    def validate_data(self, instance, model_obj=None):
        if FacilityReportTemplate.objects.filter(
            type=instance.type, facility=self.get_facility_obj()
        ).exists():
            raise ValidationError(
                detail=f"Report template with type {instance.type.value} already exists for this facility"
            )

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    @action(detail=False, methods=["GET"])
    def get_available_section_source(self, request, *args, **kwargs):
        return Response(SectionRegistry.all().keys(), status=status.HTTP_200_OK)
