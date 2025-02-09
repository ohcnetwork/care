from django.db import transaction
from django.utils import timezone
from django_filters import rest_framework as filters
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet, EMRModelViewSet
from care.emr.models import (
    Device,
    DeviceEncounterHistory,
    DeviceLocationHistory,
    Encounter,
    FacilityLocation,
)
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.resources.device.spec import (
    DeviceCreateSpec,
    DeviceEncounterHistoryListSpec,
    DeviceListSpec,
    DeviceLocationHistoryListSpec,
    DeviceRetrieveSpec,
    DeviceUpdateSpec,
)
from care.facility.models import Facility


class DeviceFilters(filters.FilterSet):
    current_location = filters.UUIDFilter(field_name="current_location__external_id")
    current_encounter = filters.UUIDFilter(field_name="current_encounter__external_id")


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

    class DeviceEncounterAssociationRequest(BaseModel):
        encounter: UUID4

    @action(detail=True, methods=["POST"])
    def associate_encounter(self, request, *args, **kwargs):
        request_data = self.DeviceEncounterAssociationRequest(**request.data)
        encounter = get_object_or_404(Encounter, external_id=request_data.encounter)
        device = self.get_object()
        # TODO Perform Authz for encounter
        if device.current_encounter_id == encounter.id:
            raise ValidationError("Encounter already associated")
        with transaction.atomic():
            if device.current_encounter:
                old_obj = DeviceEncounterHistory.objects.filter(
                    device=device, encounter=device.current_encounter, end__isnull=True
                ).first()
                if old_obj:
                    old_obj.end = timezone.now()
                    old_obj.save()
            device.current_encounter = encounter
            device.save(update_fields=["current_encounter"])
            DeviceEncounterHistory.objects.create(
                device=device, encounter=encounter, start=timezone.now()
            )

    class DeviceLocationAssociationRequest(BaseModel):
        location: UUID4

    @action(detail=True, methods=["POST"])
    def associate_location(self, request, *args, **kwargs):
        request_data = self.DeviceLocationAssociationRequest(**request.data)
        location = get_object_or_404(
            FacilityLocation, external_id=request_data.location
        )
        device = self.get_object()
        # TODO Perform Authz for location
        if device.current_location == location.id:
            raise ValidationError("Location already associated")
        with transaction.atomic():
            if device.current_location:
                old_obj = DeviceLocationHistory.objects.filter(
                    device=device, location=device.current_location, end__isnull=True
                ).first()
                if old_obj:
                    old_obj.end = timezone.now()
                    old_obj.save()
            device.current_location = location
            device.save(update_fields=["current_location"])
            DeviceLocationHistory.objects.create(
                device=device, location=location, start=timezone.now()
            )


class DeviceLocationHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceLocationHistory
    pydantic_read_model = DeviceLocationHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        return DeviceLocationHistory.objects.filter(
            device=self.get_device()
        ).select_related("location")

    # TODO Authz


class DeviceEncounterHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceLocationHistory
    pydantic_read_model = DeviceEncounterHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        return DeviceLocationHistory.objects.filter(
            device=self.get_device()
        ).select_related("encounter")


# TODO AuthZ
# TODO Serialize current location and history in the retrieve API
