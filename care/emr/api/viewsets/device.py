from django.db import transaction
from django.utils import timezone
from django_filters import rest_framework as filters
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

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
from care.security.authorization import AuthorizationController


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

    def authorize_create(self, instance):
        if not AuthorizationController.call("can_manage_devices", self.request.user):
            raise PermissionDenied("You do not have permission to create device")

    def authorize_update(self, instance, model_instance):
        if not AuthorizationController.call("can_manage_devices", self.request.user):
            raise PermissionDenied("You do not have permission to update device")

    def authorize_destroy(self, instance):
        if not AuthorizationController.call("can_manage_devices", self.request.user):
            raise PermissionDenied("You do not have permission to delete device")

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
            # TODO Check access to location with permission and then allow filter with or,
            # Access should not be limited by location if the device has org access
            # If location access then allow all, otherwise apply organization filter
        else:
            queryset = queryset.filter(
                facility_organization_cache__overlap=users_facility_organizations
            )

        return queryset

    class DeviceEncounterAssociationRequest(BaseModel):
        encounter: UUID4 | None = None

    @action(detail=True, methods=["POST"])
    def associate_encounter(self, request, *args, **kwargs):
        request_data = self.DeviceEncounterAssociationRequest(**request.data)
        encounter = None
        if request_data.encounter:
            encounter = get_object_or_404(Encounter, external_id=request_data.encounter)
        device = self.get_object()
        facility = self.get_facility_obj()

        if not AuthorizationController.call(
            "can_associate_device_encounter", self.request.user, facility
        ):
            raise PermissionDenied(
                "You do not have permission to associate encounter to this device"
            )

        if encounter and device.current_encounter_id == encounter.id:
            raise ValidationError("Encounter already associated")
        if encounter and encounter.facility_id != facility.id:
            raise ValidationError("Encounter is not part of given facility")
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
            if encounter:
                obj = DeviceEncounterHistory.objects.create(
                    device=device,
                    encounter=encounter,
                    start=timezone.now(),
                    created_by=request.user,
                )
                return Response(DeviceEncounterHistoryListSpec.serialize(obj).to_json())
            return Response({})

    class DeviceLocationAssociationRequest(BaseModel):
        location: UUID4 | None = None

    @action(detail=True, methods=["POST"])
    def associate_location(self, request, *args, **kwargs):
        request_data = self.DeviceLocationAssociationRequest(**request.data)
        location = None
        if request_data.location:
            location = get_object_or_404(
                FacilityLocation, external_id=request_data.location
            )
        facility = self.get_facility_obj()
        device = self.get_object()

        if not AuthorizationController.call(
            "can_associate_device_location", self.request.user, facility
        ):
            raise PermissionDenied(
                "You do not have permission to associate location to this device"
            )
        if location and device.current_location_id == location.id:
            raise ValidationError("Location already associated")
        if location and location.facility_id != facility.id:
            raise ValidationError("Location is not part of given facility")
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
            if location:
                obj = DeviceLocationHistory.objects.create(
                    device=device,
                    location=location,
                    start=timezone.now(),
                    created_by=request.user,
                )
                return Response(DeviceLocationHistoryListSpec.serialize(obj).to_json())
            return Response({})


class DeviceLocationHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceLocationHistory
    pydantic_read_model = DeviceLocationHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_list_devices",
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to access the device")

        return (
            DeviceLocationHistory.objects.filter(device=self.get_device())
            .select_related("location")
            .order_by("-end")
        )


class DeviceEncounterHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceEncounterHistory
    pydantic_read_model = DeviceEncounterHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_list_devices",
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to access the device")

        return (
            DeviceEncounterHistory.objects.filter(device=self.get_device())
            .select_related("encounter", "encounter__patient", "encounter__facility")
            .order_by("-end")
        )
