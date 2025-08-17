from typing import Literal

from django.db import transaction
from django.db.models.expressions import Subquery
from django_filters import CharFilter, DateFromToRangeFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from pydantic import UUID4, BaseModel
from rest_framework import filters as rest_framework_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
)
from care.emr.api.viewsets.scheduling import lock_create_appointment
from care.emr.models import TokenSlot
from care.emr.models.scheduling import SchedulableUserResource, TokenBooking
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    BookingStatusChoices,
    TokenBookingReadSpec,
    TokenBookingWriteSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.resources.user.spec import UserSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.filters.multiselect import MultiSelectFilter


class CancelBookingSpec(BaseModel):
    reason: Literal[
        BookingStatusChoices.cancelled,
        BookingStatusChoices.entered_in_error,
        BookingStatusChoices.rescheduled,
    ]
    note: str | None = None


class RescheduleBookingSpec(BaseModel):
    new_slot: UUID4
    new_booking_note: str
    previous_booking_note: str | None = None

    tags: list[UUID4] = []


class TokenBookingFilters(FilterSet):
    status = MultiSelectFilter(field_name="status")
    date = DateFromToRangeFilter(field_name="token_slot__start_datetime__date")
    slot = UUIDFilter(field_name="token_slot__external_id")
    user = CharFilter(method="filter_by_users")
    patient = UUIDFilter(field_name="patient__external_id")

    def filter_by_users(self, queryset, name, value):
        user_external_ids = value.split(",") if value else []
        if not user_external_ids:
            return queryset
        facility = get_object_or_404(
            Facility.objects.only("id"),
            external_id=self.request.parser_context.get("kwargs", {}).get(
                "facility_external_id"
            ),
        )

        token_slots = TokenSlot.objects.filter(
            resource_id__in=Subquery(
                SchedulableUserResource.objects.filter(
                    user_id__in=Subquery(
                        User.objects.filter(external_id__in=user_external_ids).values(
                            "id"
                        )
                    ),
                    facility_id=facility.id,
                ).values("id")
            )
        ).values_list("id", flat=True)
        if not token_slots:
            return queryset.none()

        return queryset.filter(token_slot__in=token_slots)


class TokenBookingViewSet(
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRTagMixin,
):
    database_model = TokenBooking
    pydantic_model = TokenBookingWriteSpec
    pydantic_read_model = TokenBookingReadSpec
    pydantic_update_model = TokenBookingWriteSpec

    filterset_class = TokenBookingFilters
    filter_backends = [
        DjangoFilterBackend,
        SingleFacilityTagFilter,
        rest_framework_filters.OrderingFilter,
    ]

    ordering_fields = ["created_date", "token_slot__start_datetime"]

    resource_type = TagResource.token_booking

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_facility_from_instance(self, instance):
        return instance.token_slot.resource.facility

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_user_booking",
            self.request.user,
            model_instance.token_slot.resource.facility,
            model_instance.token_slot.resource.user,
        ):
            raise PermissionDenied("You do not have permission to update bookings")

    def get_queryset(self):
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_list_facility_user_booking", self.request.user, facility
        ):
            raise PermissionDenied("You do not have permission to view user schedule")
        return (
            super()
            .get_queryset()
            .filter(token_slot__resource__facility=facility)
            .select_related(
                "token_slot",
                "patient",
                "patient__geo_organization",
                "token_slot__availability",
                "token_slot__resource",
            )
            .order_by("-modified_date")
        )

    @classmethod
    def cancel_appointment_handler(cls, instance, request_data, user):
        request_data = CancelBookingSpec(**request_data)
        if instance.status == BookingStatusChoices.in_consultation:
            raise ValidationError("You cannot cancel an appointment In-Consultation")
        with transaction.atomic():
            if instance.status not in CANCELLED_STATUS_CHOICES:
                # Free up the slot if it is not cancelled already
                instance.token_slot.allocated -= 1
                instance.token_slot.save()
            if request_data.note:
                instance.note = request_data.note
            instance.status = request_data.reason
            instance.updated_by = user
            instance.save()
        return Response(
            TokenBookingReadSpec.serialize(instance).model_dump(exclude=["meta"])
        )

    @action(detail=True, methods=["POST"])
    def cancel(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        return self.cancel_appointment_handler(instance, request.data, request.user)

    @action(detail=True, methods=["POST"])
    def reschedule(self, request, *args, **kwargs):
        request_data = RescheduleBookingSpec(**request.data)
        existing_booking = self.get_object()
        facility = self.get_facility_obj()
        self.authorize_update({}, existing_booking)
        if not AuthorizationController.call(
            "can_reschedule_appointment", self.request.user, facility
        ):
            raise PermissionDenied(
                "You do not have permission to reschedule appointments"
            )
        new_slot = get_object_or_404(
            TokenSlot,
            external_id=request_data.new_slot,
            resource__facility_id=facility.id,
        )
        if existing_booking.token_slot.id == new_slot.id:
            raise ValidationError("Cannot reschedule to the same slot")

        with transaction.atomic():
            self.cancel_appointment_handler(
                existing_booking,
                {
                    "reason": BookingStatusChoices.rescheduled,
                    "note": request_data.previous_booking_note or existing_booking.note,
                },
                request.user,
            )
            appointment = lock_create_appointment(
                new_slot,
                existing_booking.patient,
                request.user,
                request_data.new_booking_note,
            )
            if request_data.tags:
                tag_manager = SingleFacilityTagManager()
                tag_manager.set_tags(
                    TagResource.token_booking,
                    appointment,
                    request_data.tags,
                    request.user,
                    facility,
                )
            return Response(
                TokenBookingReadSpec.serialize(appointment).model_dump(exclude=["meta"])
            )

    @action(detail=False, methods=["GET"])
    def available_users(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        user_resources = SchedulableUserResource.objects.filter(
            facility=facility,
            user__deleted=False,
        )

        return Response(
            {
                "users": [
                    UserSpec.serialize(user_resource.user).to_json()
                    for user_resource in user_resources
                ]
            }
        )
