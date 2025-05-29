from django.db import transaction
from django.utils import timezone
from django_filters import rest_framework as filters
from pydantic import UUID4, BaseModel
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRModelReadOnlyViewSet,
    EMRModelViewSet,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models import (
    Device,
    DeviceEncounterHistory,
    DeviceLocationHistory,
    DeviceServiceHistory,
    Encounter,
    FacilityLocation,
)
from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.emr.registries.device_type.device_registry import DeviceTypeRegistry
from care.emr.resources.device.history_spec import (
    DeviceServiceHistoryListSpec,
    DeviceServiceHistoryRetrieveSpec,
    DeviceServiceHistoryWriteSpec,
)
from care.emr.resources.device.spec import (
    DeviceCreateSpec,
    DeviceEncounterHistoryListSpec,
    DeviceListSpec,
    DeviceLocationHistoryListSpec,
    DeviceRetrieveSpec,
    DeviceUpdateSpec,
)
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.facility.models import Facility
from care.security.authorization import AuthorizationController


class DeviceFilters(filters.FilterSet):
    current_encounter = filters.UUIDFilter(field_name="current_encounter__external_id")
    current_location = filters.UUIDFilter(field_name="current_location__external_id")
    care_type = filters.CharFilter(field_name="care_type")


class DeviceViewSet(EMRModelViewSet):
    database_model = Device
    pydantic_model = DeviceCreateSpec
    pydantic_update_model = DeviceUpdateSpec
    pydantic_read_model = DeviceListSpec
    pydantic_retrieve_model = DeviceRetrieveSpec
    filterset_class = DeviceFilters
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ["registered_name", "user_friendly_name"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_create_device", self.request.user, facility
        ):
            raise PermissionDenied("You do not have permission to create device")

    def authorize_update(self, instance, model_instance):
        if not AuthorizationController.call(
            "can_manage_device", self.request.user, model_instance
        ):
            raise PermissionDenied("You do not have permission to update device")

    def authorize_destroy(self, instance):
        self.authorize_update(None, instance)

    def perform_create(self, instance):
        instance.facility = self.get_facility_obj()
        with transaction.atomic():
            super().perform_create(instance)
            if instance.care_type:
                care_device_class = DeviceTypeRegistry.get_care_device_class(
                    instance.care_type
                )
                care_device_class().handle_create(self.request.data, instance)

    def perform_update(self, instance):
        with transaction.atomic():
            super().perform_update(instance)
            if instance.care_type:
                care_device_class = DeviceTypeRegistry.get_care_device_class(
                    instance.care_type
                )
                care_device_class().handle_update(self.request.data, instance)

    def perform_destroy(self, instance):
        with transaction.atomic():
            if instance.care_type:
                care_device_class = DeviceTypeRegistry.get_care_device_class(
                    instance.care_type
                )
                care_device_class().handle_delete(instance)
            super().perform_destroy(instance)

    def get_queryset(self):
        """
        When Location is specified, Location permission is checked (or) organization filters are applied
        If location is not specified the organization cache is used
        """
        queryset = Device.objects.all()

        facility = self.get_facility_obj()
        facility_organizations = FacilityOrganization.objects.filter(
            facility=facility
        ).values_list("id", flat=True)

        if self.request.user.is_superuser:
            users_facility_organizations = facility_organizations
        else:
            users_facility_organizations = FacilityOrganizationUser.objects.filter(
                organization_id__in=facility_organizations, user=self.request.user
            ).values_list("organization_id", flat=True)

        if "location" in self.request.GET:
            location = get_object_or_404(
                FacilityLocation, external_id=self.request.GET["location"]
            )
            if AuthorizationController.call(
                "can_read_devices_on_location", self.request.user, location
            ):
                queryset = queryset.filter(current_location=location)
            else:
                queryset = queryset.filter(
                    facility_organization_cache__overlap=users_facility_organizations,
                    current_location=location,
                )
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

        if encounter and device.current_encounter_id == encounter.id:
            raise ValidationError("Encounter already associated")
        if encounter and encounter.facility_id != facility.id:
            raise ValidationError("Encounter is not part of given facility")

        if not AuthorizationController.call(
            "can_manage_device_associations_to_encounters", self.request.user, device
        ):
            raise PermissionDenied("You do not have permission to associate device")

        if encounter and not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, encounter
        ):
            raise PermissionDenied(
                "You do not have permission to associate encounter to this device"
            )

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

        if location and device.current_location_id == location.id:
            raise ValidationError("Location already associated")
        if location and location.facility_id != facility.id:
            raise ValidationError("Location is not part of given facility")

        self.authorize_update(None, device)

        if location and not AuthorizationController.call(
            "can_update_facility_location_obj", self.request.user, location
        ):
            raise PermissionDenied(
                "You do not have permission to associate location to this device"
            )
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

    class DeviceManageOrganizationRequest(BaseModel):
        managing_organization: UUID4

    @action(detail=True, methods=["POST"])
    def add_managing_organization(self, request, *args, **kwargs):
        request_data = self.DeviceManageOrganizationRequest(**request.data)
        device = self.get_object()
        facility = self.get_facility_obj()
        organization = get_object_or_404(
            FacilityOrganization, external_id=request_data.managing_organization
        )
        if organization.facility_id != facility.id:
            raise ValidationError("Organization is not part of given facility")

        self.authorize_update(None, device)
        if not AuthorizationController.call(
            "can_manage_facility_organization_obj", request.user, organization
        ):
            raise PermissionDenied(
                "You do not have permission to manage facility organization"
            )
        if Device.objects.filter(
            id=device.id, managing_organization=organization
        ).exists():
            raise ValidationError("Organization is already associated with this device")
        device.managing_organization = organization
        device.save(
            update_fields=["managing_organization", "facility_organization_cache"]
        )
        return Response({})

    @action(detail=True, methods=["POST"])
    def remove_managing_organization(self, request, *args, **kwargs):
        device = self.get_object()

        if device.managing_organization is None:
            raise ValidationError(
                "No managing organization is associated with this device"
            )
        self.authorize_update(None, device)
        if not AuthorizationController.call(
            "can_manage_facility_organization_obj",
            request.user,
            device.managing_organization,
        ):
            raise PermissionDenied(
                "You do not have permission to manage facility organization"
            )

        device.managing_organization = None
        device.save(
            update_fields=["managing_organization", "facility_organization_cache"]
        )
        return Response({})


class DeviceLocationHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceLocationHistory
    pydantic_read_model = DeviceLocationHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        device = self.get_device()
        if not AuthorizationController.call(
            "can_read_device", self.request.user, device
        ):
            raise PermissionDenied("You do not have permission to access the device")

        return (
            DeviceLocationHistory.objects.filter(device=device)
            .select_related("location")
            .order_by("-end")
        )


class DeviceEncounterHistoryViewSet(EMRModelReadOnlyViewSet):
    database_model = DeviceEncounterHistory
    pydantic_read_model = DeviceEncounterHistoryListSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def get_queryset(self):
        """
        Encounter history access is limited to everyone within the location or associated with the managing org
        """
        device = self.get_device()
        if not AuthorizationController.call(
            "can_read_device",
            self.request.user,
            device,
        ):
            raise PermissionDenied("You do not have permission to access the device")
        return (
            DeviceEncounterHistory.objects.filter(device=device)
            .select_related("encounter", "encounter__patient", "encounter__facility")
            .order_by("-end")
        )


class DeviceServiceHistoryViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = DeviceServiceHistory
    pydantic_model = DeviceServiceHistoryWriteSpec
    pydantic_read_model = DeviceServiceHistoryListSpec
    pydantic_retrieve_model = DeviceServiceHistoryRetrieveSpec

    def get_device(self):
        return get_object_or_404(Device, external_id=self.kwargs["device_external_id"])

    def perform_create(self, instance):
        device = self.get_device()
        instance.device = device
        super().perform_create(instance)

    def authorize_create(self, instance):
        device = self.get_device()
        if not AuthorizationController.call(
            "can_manage_device",
            self.request.user,
            device,
        ):
            raise PermissionDenied("You do not have permission to access the device")

    def authorize_update(self, request_obj, model_instance):
        self.authorize_create(model_instance)

    def perform_update(self, instance):
        if instance.edit_history and len(instance.edit_history) >= 50:  # noqa PLR2004
            raise ValidationError("Cannot Edit instance anymore")
        if not instance.edit_history:
            instance.edit_history = []
        current_instance = DeviceServiceHistory.objects.get(id=instance.id)
        instance.edit_history.append(
            {
                "serviced_on": str(current_instance.serviced_on),
                "note": current_instance.note,
                "updated_by": current_instance.updated_by.id,
            }
        )
        super().perform_update(instance)

    def get_queryset(self):
        """
        Encounter history access is limited to everyone within the location or associated with the managing org
        """
        device = self.get_device()
        if not AuthorizationController.call(
            "can_read_device",
            self.request.user,
            device,
        ):
            raise PermissionDenied("You do not have permission to access the device")
        return DeviceServiceHistory.objects.filter(device=device).order_by(
            "-serviced_on"
        )


def disassociate_device_from_encounter(instance):
    if instance.status in COMPLETED_CHOICES:
        with transaction.atomic():
            device_ids = list(
                Device.objects.filter(current_encounter=instance).values_list(
                    "id", flat=True
                )
            )
            Device.objects.filter(id__in=device_ids).update(current_encounter=None)

            DeviceEncounterHistory.objects.filter(
                device_id__in=device_ids, encounter=instance, end__isnull=True
            ).update(end=timezone.now())
