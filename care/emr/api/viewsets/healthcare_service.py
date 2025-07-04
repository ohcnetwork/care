from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.resources.healthcare_service.spec import (
    HealthcareServiceReadSpec,
    HealthcareServiceRetrieveSpec,
    HealthcareServiceWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController


class HealthcareServiceFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    name = filters.CharFilter(lookup_expr="icontains")
    internal_type = filters.CharFilter(lookup_expr="iexact")


class HealthcareServiceViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = HealthcareService
    pydantic_model = HealthcareServiceWriteSpec
    pydantic_read_model = HealthcareServiceReadSpec
    pydantic_retrieve_model = HealthcareServiceRetrieveSpec
    filterset_class = HealthcareServiceFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def convert_external_id_to_internal_id(self, instance):
        ids = []
        for location in instance.locations:
            obj = (
                FacilityLocation.objects.only("id")
                .filter(external_id=location, facility=instance.facility)
                .first()
            )
            if not obj:
                error_msg = f"Location with id {location} not found"
                raise ValidationError(error_msg)
            ids.append(obj.id)
        instance.locations = ids

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        self.convert_external_id_to_internal_id(instance)
        super().perform_create(instance)

    def perform_update(self, instance):
        self.convert_external_id_to_internal_id(instance)
        return super().perform_update(instance)

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_facility_healthcare_service",
            self.request.user,
            self.get_facility_obj(),
        ):
            raise PermissionDenied("Access Denied to Healthcare Service")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_facility_healthcare_service",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Healthcare Service")

    def get_queryset(self):
        base_queryset = super().get_queryset()
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_healthcare_service",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Healthcare Service")
        return base_queryset.filter(facility=facility)
