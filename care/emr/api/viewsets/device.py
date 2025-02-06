from django_filters import rest_framework as filters
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import Device
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.resources.device.spec import (
    DeviceCreateSpec,
    DeviceListSpec,
    DeviceRetrieveSpec,
    DeviceUpdateSpec,
)
from care.facility.models import Facility


class DeviceFilters(filters.FilterSet):
    pass


class DeviceViewSet(EMRModelViewSet):
    database_model = Device
    pydantic_model = DeviceCreateSpec
    pydantic_update_model = DeviceUpdateSpec
    pydantic_read_model = DeviceListSpec
    pydantic_retrieve_model = DeviceRetrieveSpec
    filterset_class = DeviceFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    def get_queryset(self):
        """
        When Location is specified, Location permission is checked (or) organization filters are applied
        If location is not specified the organization cache is used
        """
        queryset = Device.objects.all()

        if self.request.user.is_superuser:
            return queryset

        facility = self.get_facility_obj()

        users_facility_organizations = FacilityOrganizationUser.objects.filter(
            organization__facility=facility, user=self.request.user
        ).values_list("organization_id", flat=True)

        if "location" in self.request.GET:
            queryset = queryset.filter(
                facility_organization_cache__overlap=users_facility_organizations
            )
            # TODO Check access to location with permission and then allow filter
            # If location access then allow all, otherwise apply organization filter
        else:
            queryset = queryset.filter(
                facility_organization_cache__overlap=users_facility_organizations
            )

        return queryset

    # TODO Action for Associating Encounter
    # TODO Action for Associating Location
    # TODO RO API's for Device Location and Encounter History
    # TODO Serialize current location and history in the retrieve API
