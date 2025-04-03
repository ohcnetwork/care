from django.conf import settings
from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework import filters as rest_framework_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRModelViewSet,
)
from care.emr.models import (
    Encounter,
    FacilityLocation,
    FacilityLocationEncounter,
    FacilityLocationOrganization,
)
from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.location.spec import (
    FacilityLocationEncounterCreateSpec,
    FacilityLocationEncounterReadSpec,
    FacilityLocationEncounterUpdateSpec,
    FacilityLocationListSpec,
    FacilityLocationModeChoices,
    FacilityLocationRetrieveSpec,
    FacilityLocationUpdateSpec,
    FacilityLocationWriteSpec,
    LocationEncounterAvailabilityStatusChoices,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.utils.lock import Lock
from care.utils.time_util import care_now


class AvailabilityFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value is None:
            return qs
        if value:
            return qs.filter(current_encounter__isnull=True)
        return qs.filter(current_encounter__isnull=False)


class FacilityLocationFilter(filters.FilterSet):
    parent = filters.UUIDFilter(field_name="parent__external_id")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    mode = filters.CharFilter(field_name="mode", lookup_expr="iexact")
    form = filters.CharFilter(field_name="form", lookup_expr="iexact")
    operational_status = filters.CharFilter(
        field_name="operational_status", lookup_expr="iexact"
    )
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    available = AvailabilityFilter(field_name="available")


class FacilityLocationViewSet(EMRModelViewSet):
    database_model = FacilityLocation
    pydantic_model = FacilityLocationWriteSpec
    pydantic_read_model = FacilityLocationListSpec
    pydantic_retrieve_model = FacilityLocationRetrieveSpec
    pydantic_update_model = FacilityLocationUpdateSpec
    filterset_class = FacilityLocationFilter
    filter_backends = [
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    ]
    ordering_fields = ["sort_index"]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def validate_destroy(self, instance):
        # Validate that there is no children if exists
        if FacilityLocation.objects.filter(parent=instance).exists():
            raise ValidationError("Location has active children")
        # TODO Add validation to check if patient association exists

    def perform_destroy(self, instance):
        parent = instance.parent
        with transaction.atomic():
            super().perform_destroy(instance)
            if parent:
                parent.has_children = FacilityLocation.objects.filter(
                    parent=parent
                ).exists()
                parent.save(update_fields=["has_children"])

    def validate_data(self, instance, model_obj=None):
        facility = self.get_facility_obj()
        if model_obj is None and instance.parent:
            parent = get_object_or_404(FacilityLocation, external_id=instance.parent)
            if parent.facility_id != facility.id:
                raise PermissionDenied("Parent Incompatible with Location")
            if parent.mode == FacilityLocationModeChoices.instance.value:
                raise ValidationError("Instances cannot have children")

            # Validate Depth
            if parent.level_cache >= settings.LOCATION_MAX_DEPTH:
                error = f"Max depth reached ({settings.LOCATION_MAX_DEPTH})"
                raise ValidationError(error)

        if model_obj is None:
            # validate number of locations in facility
            facility_external_id = self.kwargs["facility_external_id"]
            if (
                FacilityLocation.objects.filter(
                    facility__external_id=facility_external_id
                ).count()
                >= settings.MAX_LOCATION_IN_FACILITY
            ):
                error = f"Max location reached for facility ({settings.MAX_LOCATION_IN_FACILITY})"
                raise ValidationError(error)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        if instance.parent:
            parent = get_object_or_404(FacilityLocation, external_id=instance.parent)
        else:
            parent = None
        if not AuthorizationController.call(
            "can_create_facility_location_obj", self.request.user, parent, facility
        ):
            raise PermissionDenied("You do not have permission to create a location")
        if instance.organizations:
            for organization in instance.organizations:
                organization_obj = get_object_or_404(
                    FacilityOrganization, external_id=organization
                )
                self.authorize_organization(facility, organization_obj)

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_update_facility_location_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("You do not have permission to update this location")

    def authorize_destroy(self, instance):
        self.authorize_update({}, instance)

    def perform_create(self, instance):
        facility = self.get_facility_obj()
        instance.facility = facility
        return super().perform_create(instance)

    def get_queryset(self):
        facility = self.get_facility_obj()
        base_qs = FacilityLocation.objects.filter(facility=facility)

        if "parent" in self.request.GET and not self.request.GET.get("parent"):
            # Filter for root location, For some reason its not working as intended in Django Filters
            base_qs = base_qs.filter(parent__isnull=True)

        if "mine" in self.request.GET:
            # Filter based on direct association
            organization_ids = list(
                FacilityOrganizationUser.objects.filter(
                    user=self.request.user, organization__facility=facility
                ).values_list("organization_id", flat=True)
            )
            base_qs = base_qs.filter(
                id__in=FacilityLocationOrganization.objects.filter(
                    organization_id__in=organization_ids
                ).values_list("location_id", flat=True)
            )
        return AuthorizationController.call(
            "get_accessible_facility_locations", base_qs, self.request.user, facility
        )

    @action(detail=True, methods=["GET"])
    def organizations(self, request, *args, **kwargs):
        # AuthZ is controlled from the get_queryset method, no need to repeat
        instance = self.get_object()
        encounter_organizations = FacilityLocationOrganization.objects.filter(
            location=instance
        ).select_related("organization")
        data = [
            FacilityOrganizationReadSpec.serialize(
                encounter_organization.organization
            ).to_json()
            for encounter_organization in encounter_organizations
        ]
        return Response({"results": data})

    class FacilityLocationOrganizationManageSpec(BaseModel):
        organization: UUID4

    def authorize_organization(self, facility, organization):
        if organization.facility.id != facility.id:
            raise PermissionDenied("Organization Incompatible with Location")
        if not AuthorizationController.call(
            "can_manage_facility_organization_obj", self.request.user, organization
        ):
            raise PermissionDenied("You do not have permission to given organizations")

    @extend_schema(
        request=FacilityLocationOrganizationManageSpec,
        responses={200: FacilityOrganizationReadSpec},
    )
    @action(detail=True, methods=["POST"])
    def organizations_add(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.FacilityLocationOrganizationManageSpec(**request.data)
        organization = get_object_or_404(
            FacilityOrganization, external_id=request_data.organization
        )
        self.authorize_update({}, instance)
        self.authorize_organization(instance.facility, organization)
        location_organization = FacilityLocationOrganization.objects.filter(
            location=instance, organization=organization
        )
        if location_organization.exists():
            raise ValidationError("Organization already exists")
        FacilityLocationOrganization.objects.create(
            location=instance, organization=organization
        )
        return Response(FacilityOrganizationReadSpec.serialize(organization).to_json())

    @extend_schema(
        request=FacilityLocationOrganizationManageSpec, responses={200: None}
    )
    @action(detail=True, methods=["POST"])
    def organizations_remove(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.FacilityLocationOrganizationManageSpec(**request.data)
        organization = get_object_or_404(
            FacilityOrganization, external_id=request_data.organization
        )
        self.authorize_update({}, instance)
        self.authorize_organization(instance.facility, organization)
        encounter_organization = FacilityLocationOrganization.objects.filter(
            location=instance, organization=organization
        )
        if not encounter_organization.exists():
            raise ValidationError("Organization does not exist")
        FacilityLocationOrganization.objects.filter(
            location=instance, organization=organization
        ).delete()
        instance.save()  # Recalculate Metadata
        instance.cascade_changes()  # Recalculate Metadata for children as well.
        return Response({})

    class FacilityLocationEncounterAssignSpec(BaseModel):
        encounter: UUID4

    @extend_schema(request=FacilityLocationEncounterAssignSpec)
    @action(detail=True, methods=["POST"])
    def associate_encounter(self, request, *args, **kwargs):
        instance = self.get_object()
        facility = self.get_facility_obj()
        request_data = self.FacilityLocationEncounterAssignSpec(**request.data)
        encounter = get_object_or_404(Encounter, external_id=request_data.encounter)
        if instance.facility_id != encounter.facility_id:
            raise PermissionDenied("Encounter Incompatible with Location")
        if not AuthorizationController.call(
            "can_list_facility_location_obj", self.request.user, facility, instance
        ):
            raise PermissionDenied("You do not have permission to given location")
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")
        # TODO, Association models yet to be built


class FacilityLocationEncounterFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")


class FacilityLocationEncounterViewSet(EMRModelViewSet):
    database_model = FacilityLocationEncounter
    pydantic_model = FacilityLocationEncounterCreateSpec
    pydantic_read_model = FacilityLocationEncounterReadSpec
    pydantic_update_model = FacilityLocationEncounterUpdateSpec
    filterset_class = FacilityLocationEncounterFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_location_obj(self):
        return get_object_or_404(
            FacilityLocation, external_id=self.kwargs["location_external_id"]
        )

    def authorize_update(self, request_obj, model_instance):
        return self.authorize_create(model_instance)

    def authorize_destroy(self, instance):
        return self.authorize_create(instance)

    def reset_encounter_location_association(self, location):
        """
        Reset encounters to the right location.
        """
        active_location_encounter = FacilityLocationEncounter.objects.filter(
            location=location,
            status=LocationEncounterAvailabilityStatusChoices.active.value,
        ).first()
        all_encounters = Encounter.objects.filter(current_location=location)
        if active_location_encounter:
            active_location_encounter.encounter.current_location = location
            active_location_encounter.encounter.save(update_fields=["current_location"])
            all_encounters = all_encounters.exclude(
                id=active_location_encounter.encounter_id
            )
            location.current_encounter = active_location_encounter.encounter
        else:
            location.current_encounter = None
        all_encounters.update(current_location=None)
        location.save(update_fields=["current_encounter"])

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        location = self.get_location_obj()
        encounter = instance.encounter
        if not isinstance(instance.encounter, Encounter):
            encounter = get_object_or_404(Encounter, external_id=encounter)
        if location.facility_id != encounter.facility_id:
            raise PermissionDenied("Encounter Incompatible with Location")
        if not AuthorizationController.call(
            "can_list_facility_location_obj", self.request.user, facility, location
        ):
            raise PermissionDenied("You do not have permission to given location")
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def perform_create(self, instance):
        location = self.get_location_obj()
        with Lock(f"facility_location:{location.id}"):
            instance.location = location
            self._validate_data(instance)
            super().perform_create(instance)
            self.reset_encounter_location_association(location)

    def perform_update(self, instance):
        location = self.get_location_obj()
        with Lock(f"facility_location:{location.id}"):
            # Keep in mind that instance here is an ORM instance and not pydantic
            self._validate_data(instance, self.get_object())
            super().perform_update(instance)
            self.reset_encounter_location_association(location)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        self.reset_encounter_location_association(instance.location)

    def _validate_data(self, instance, model_obj=None):  # noqa PLR0912
        """
        This method will be called separately to maintain a lock when the validation is being performed
        """
        location = self.get_location_obj()
        if location.mode == FacilityLocationModeChoices.kind.value:
            raise ValidationError("Cannot assign encounters to location kind")

        start_datetime = instance.start_datetime
        base_qs = FacilityLocationEncounter.objects.all()
        if model_obj:
            encounter = model_obj.encounter
        else:
            encounter = instance.encounter
            if not isinstance(instance.encounter, Encounter):
                encounter = get_object_or_404(Encounter, external_id=encounter)
        if model_obj:
            # Validate if the current dates are not in conflict with other dates
            base_qs = base_qs.exclude(id=model_obj.id)
        status = instance.status or model_obj.status
        if instance.end_datetime is not None:
            end_datetime = instance.end_datetime
        elif model_obj:
            end_datetime = model_obj.end_datetime
        else:
            end_datetime = None

        # Active status should not have end_datetime
        if status in (LocationEncounterAvailabilityStatusChoices.active.value):
            end_datetime = None

        # Validate end time is greater than start time
        if end_datetime and start_datetime > end_datetime:
            raise ValidationError("End Datetime should be greater than Start Datetime")
        # Completed, reserved or planned status should have end_datetime
        if (
            status
            in (
                LocationEncounterAvailabilityStatusChoices.completed.value,
                LocationEncounterAvailabilityStatusChoices.reserved.value,
                LocationEncounterAvailabilityStatusChoices.planned.value,
            )
            and not end_datetime
        ):
            raise ValidationError("End Datetime is required for completed status")

        # Ensure that there is no conflict in the schedule
        if end_datetime:
            if (
                base_qs.filter(location=location)
                .filter(
                    start_datetime__lte=end_datetime, end_datetime__gte=start_datetime
                )
                .exists()
            ):
                raise ValidationError("Conflict in schedule")
        elif (
            base_qs.filter(location=location)
            .filter(start_datetime__gte=start_datetime)
            .exists()
        ):
            raise ValidationError("Conflict in schedule")

        # Ensure that there is no other association at this point
        if (
            status == LocationEncounterAvailabilityStatusChoices.active.value
            and base_qs.filter(location=location)
            .filter(status=LocationEncounterAvailabilityStatusChoices.active.value)
            .exists()
        ):
            raise ValidationError(
                "Another active encounter already exists for this location"
            )

        # Ensure that there is no other active location on the encounter
        if (
            status == LocationEncounterAvailabilityStatusChoices.active.value
            and base_qs.filter(encounter=encounter)
            .filter(status=LocationEncounterAvailabilityStatusChoices.active.value)
            .exists()
        ):
            raise ValidationError(
                "Another active location already exists for this encounter"
            )

        # Don't allow changes to the status once the status has reached completed

        if (
            model_obj
            and model_obj.status
            == LocationEncounterAvailabilityStatusChoices.completed.value
            and instance.status != model_obj.status
        ):
            raise ValidationError("Cannot change status after marking completed")

    def get_queryset(self):
        location = self.get_location_obj()
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_location_obj", self.request.user, facility, location
        ):
            raise PermissionDenied("You do not have permission to given location")
        return FacilityLocationEncounter.objects.filter(location=location)


def close_related_location_from_encounter(instance):
    if instance.status in COMPLETED_CHOICES:
        with transaction.atomic():
            FacilityLocation.objects.filter(current_encounter=instance).update(
                current_encounter=None
            )
            FacilityLocationEncounter.objects.filter(encounter=instance).exclude(
                status__in=COMPLETED_CHOICES
            ).update(
                end_datetime=care_now(),
                status=LocationEncounterAvailabilityStatusChoices.completed.value,
            )
