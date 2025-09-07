from django.db import transaction
from django.utils import timezone
from django_filters import DateTimeFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRModelViewSet,
)
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.healthcare_service import HealthcareService
from care.emr.models.location import FacilityLocation
from care.emr.models.organization import FacilityOrganizationUser
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.models.scheduling.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
)
from care.emr.resources.scheduling.schedule.spec import (
    AvailabilityCreateSpec,
    AvailabilityForScheduleSpec,
    SchedulableResourceTypeOptions,
    ScheduleCreateSpec,
    ScheduleReadSpec,
    ScheduleUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.lock import Lock


class ChargeItemDefinitionSetSpec(BaseModel):
    charge_item_definition: str
    re_visit_allowed_days: int
    re_visit_charge_item_definition: str | None = None


class ScheduleFilters(FilterSet):
    user = UUIDFilter(field_name="resource__user__external_id")
    valid_from = DateTimeFilter(field_name="valid_to", lookup_expr="gte")
    valid_to = DateTimeFilter(field_name="valid_from", lookup_expr="lte")


def validate_resource(
    resource_type: SchedulableResourceTypeOptions, resource_id, facility: Facility
):
    """
    Validate a schedulable resource based on the resource type
    """

    if resource_type == SchedulableResourceTypeOptions.practitioner.value:
        schedule_user = get_object_or_404(
            User.objects.only("id"), external_id=resource_id
        )
        if not FacilityOrganizationUser.objects.filter(
            user=schedule_user, organization__facility=facility
        ).exists():
            raise ValidationError("Schedule User is not part of the facility")
        return schedule_user
    if resource_type == SchedulableResourceTypeOptions.healthcare_service.value:
        healthcare_service_obj = get_object_or_404(
            HealthcareService.objects.only("id"),
            external_id=resource_id,
        )
        if healthcare_service_obj.facility != facility:
            raise ValidationError("Healthcare Service is not part of the facility")
        return healthcare_service_obj
    if resource_type == SchedulableResourceTypeOptions.location.value:
        location_obj = get_object_or_404(
            FacilityLocation.objects.only("id"),
            external_id=resource_id,
        )
        if location_obj.facility != facility:
            raise ValidationError("Location is not part of the facility")
        return location_obj
    raise ValidationError("Invalid Resource Type")


def get_or_create_resource(
    resource_type: SchedulableResourceTypeOptions, resource_id, facility: Facility
):
    resource_obj = validate_resource(resource_type, resource_id, facility)
    if resource_type == SchedulableResourceTypeOptions.practitioner.value:
        resource, _ = SchedulableResource.objects.get_or_create(
            facility=facility,
            resource_type=resource_type,
            user=resource_obj,
        )
        return resource
    if resource_type == SchedulableResourceTypeOptions.healthcare_service.value:
        resource, _ = SchedulableResource.objects.get_or_create(
            facility=facility,
            resource_type=resource_type,
            healthcare_service=resource_obj,
        )
        return resource
    if resource_type == SchedulableResourceTypeOptions.location.value:
        resource, _ = SchedulableResource.objects.get_or_create(
            facility=facility,
            resource_type=resource_type,
            location=resource_obj,
        )
        return resource
    raise ValidationError("Invalid Resource Type")


class ScheduleViewSet(EMRModelViewSet):
    database_model = Schedule
    pydantic_model = ScheduleCreateSpec
    pydantic_update_model = ScheduleUpdateSpec
    pydantic_read_model = ScheduleReadSpec
    filterset_class = ScheduleFilters
    filter_backends = [DjangoFilterBackend]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        with transaction.atomic():
            resource = get_or_create_resource(
                instance._resource_type,  # noqa SLF001
                instance._resource_id,  # noqa SLF001
                self.get_facility_obj(),
            )
            instance.resource = resource
            super().perform_create(instance)
            for availability in instance.availabilities:
                availability_obj = availability.de_serialize()
                availability_obj.schedule = instance
                availability_obj.save()

    def perform_update(self, instance):
        with Lock(f"booking:resource:{instance.resource.id}"):
            super().perform_update(instance)

    def perform_destroy(self, instance):
        with Lock(f"booking:resource:{instance.resource.id}"), transaction.atomic():
            # Check if there are any tokens allocated for this schedule in the future
            availabilities = instance.availability_set.all()
            availability_ids = list(availabilities.values_list("id"))
            has_future_bookings = TokenSlot.objects.filter(
                resource=instance.resource,
                availability_id__in=availability_ids,
                start_datetime__gt=timezone.now(),
                allocated__gt=0,
            ).exists()
            if has_future_bookings:
                raise ValidationError(
                    "Cannot delete schedule as there are future bookings associated with it"
                )
            availabilities.update(deleted=True)
            slots = TokenSlot.objects.filter(
                resource=instance.resource, availability_id__in=availability_ids
            )
            slots.update(deleted=True)
            super().perform_destroy(instance)

    def authorize_create(self, instance):
        facility_obj = self.get_facility_obj()
        resource_obj = get_or_create_resource(
            instance.resource_type, instance.resource_id, facility_obj
        )
        if not AuthorizationController.call(
            "can_write_schedule", resource_obj, self.request.user
        ):
            raise PermissionDenied("You do not have permission to create schedule")

    def authorize_update(self, request_obj, model_instance):
        resource_obj = model_instance.resource
        if not AuthorizationController.call(
            "can_write_schedule", resource_obj, self.request.user
        ):
            raise PermissionDenied("You do not have permission to update schedule")

    def authorize_destroy(self, instance):
        self.authorize_update({}, instance)

    def clean_create_data(self, request_data):
        request_data["facility"] = self.kwargs["facility_external_id"]
        return request_data

    def can_read_resource_schedule(self, resource_obj):
        if not AuthorizationController.call(
            "can_list_schedule",
            resource_obj,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to update schedule")

    def authorize_retrieve(self, model_instance):
        resource_obj = model_instance.resource
        self.can_read_resource_schedule(resource_obj)

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = (
            super()
            .get_queryset()
            .select_related("resource", "created_by", "updated_by")
            .order_by("-modified_date")
        )

        if self.action == "list":
            if (
                "resource_type" not in self.request.query_params
                or "resource_id" not in self.request.query_params
            ):
                raise ValidationError("resource_type and resource_id are required")
            resource = get_or_create_resource(
                self.request.query_params["resource_type"],
                self.request.query_params["resource_id"],
                facility,
            )
            self.can_read_resource_schedule(resource)
            queryset = queryset.filter(resource=resource)
        return queryset

    @action(detail=True, methods=["POST"])
    def set_charge_item_definition(self, request, *args, **kwargs):
        schedule = self.get_object()
        request_data = ChargeItemDefinitionSetSpec(**request.data)
        if not AuthorizationController.call(
            "can_set_charge_item_definition_in_facility",
            self.request.user,
            schedule.resource.facility,
        ):
            raise PermissionDenied(
                "You do not have permission to set charge item definition"
            )
        charge_item_definition = get_object_or_404(
            ChargeItemDefinition.objects.only("id"),
            slug=request_data.charge_item_definition,
            facility=schedule.resource.facility,
        )
        schedule.charge_item_definition = charge_item_definition
        schedule.revisit_allowed_days = request_data.re_visit_allowed_days
        if request_data.re_visit_charge_item_definition:
            revisit_charge_item_definition = get_object_or_404(
                ChargeItemDefinition.objects.only("id"),
                slug=request_data.re_visit_charge_item_definition,
                facility=schedule.resource.facility,
            )
            schedule.revisit_charge_item_definition = revisit_charge_item_definition
        schedule.save()
        return Response(ScheduleReadSpec.serialize(schedule).to_json())


class AvailabilityViewSet(EMRCreateMixin, EMRDestroyMixin, EMRBaseViewSet):
    database_model = Availability
    pydantic_model = AvailabilityCreateSpec
    pydantic_retrieve_model = AvailabilityForScheduleSpec

    def get_schedule_obj(self):
        return get_object_or_404(
            Schedule, external_id=self.kwargs["schedule_external_id"]
        )

    def get_queryset(self):
        schedule_obj = self.get_schedule_obj()
        if self.action in ["list", "retrieve"] and not AuthorizationController.call(
            "can_list_schedule",
            schedule_obj.resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to list schedule")
        return (
            super()
            .get_queryset()
            .filter(schedule=schedule_obj)
            .select_related(
                "schedule",
                "schedule__resource",
                "created_by",
                "updated_by",
            )
            .order_by("-modified_date")
        )

    def clean_create_data(self, request_data):
        request_data["schedule"] = self.kwargs["schedule_external_id"]
        return request_data

    def perform_create(self, instance):
        schedule = self.get_schedule_obj()
        instance.schedule = schedule
        super().perform_create(instance)

    def perform_destroy(self, instance):
        with Lock(f"booking:resource:{instance.schedule.resource.id}"):
            has_future_bookings = TokenSlot.objects.filter(
                availability_id=instance.id,
                start_datetime__gt=timezone.now(),
                allocated__gt=0,
            ).exists()
            if has_future_bookings:
                raise ValidationError(
                    "Cannot delete availability as there are future bookings associated with it"
                )
            TokenSlot.objects.filter(availability_id=instance.id).update(deleted=True)
            super().perform_destroy(instance)

    def authorize_create(self, instance):
        schedule_obj = self.get_schedule_obj()
        if not AuthorizationController.call(
            "can_write_schedule", schedule_obj.resource, self.request.user
        ):
            raise PermissionDenied("You do not have permission to update schedule")

    def authorize_destroy(self, instance):
        self.authorize_create(None)
