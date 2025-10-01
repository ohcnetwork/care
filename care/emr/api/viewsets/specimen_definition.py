from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.specimen_definition import SpecimenDefinition
from care.emr.resources.specimen_definition.spec import (
    SpecimenDefinitionReadSpec,
    SpecimenDefinitionWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class SpecimenDefinitionFilters(filters.FilterSet):
    status = filters.CharFilter(lookup_expr="iexact")
    title = filters.CharFilter(lookup_expr="icontains")


class SpecimenDefinitionViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    lookup_field = "slug"
    database_model = SpecimenDefinition
    pydantic_model = SpecimenDefinitionWriteSpec
    pydantic_read_model = SpecimenDefinitionReadSpec
    filterset_class = SpecimenDefinitionFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def validate_data(self, instance, model_obj=None):
        facility = self.get_facility_obj() if not model_obj else model_obj.facility

        queryset = SpecimenDefinition.objects.all()

        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)

        facility_external_id = str(facility.external_id)
        slug = SpecimenDefinition.calculate_slug_from_facility(
            facility_external_id, instance.slug_value
        )

        queryset = queryset.filter(slug__iexact=slug)

        if queryset.exists():
            raise ValidationError("Specimen Definition with this slug already exists.")

        return super().validate_data(instance, model_obj)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        instance.slug = SpecimenDefinition.calculate_slug_from_facility(
            instance.facility.external_id, instance.slug
        )
        super().perform_create(instance)

    def perform_update(self, instance):
        instance.slug = SpecimenDefinition.calculate_slug_from_facility(
            instance.facility.external_id, instance.slug
        )
        super().perform_update(instance)

    def authorize_create(self, instance):
        """
        The user must have permission to create specimen definition in the facility.
        """
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_write_facility_specimen_definition",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Specimen Definition")

    def authorize_update(self, request_obj, model_instance):
        self.authorize_create(model_instance)

    def get_queryset(self):
        """
        If no facility filters are applied, all objects must be returned without a facility filter.
        If facility filter is applied, check for read permission and return all inside facility.
        """
        base_queryset = super().get_queryset()
        facility_obj = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_specimen_definition",
            self.request.user,
            facility_obj,
        ):
            raise PermissionDenied("Access Denied to Specimen Definition")
        return base_queryset.filter(facility=facility_obj)
