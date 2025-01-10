from typing import Literal

from django.db import transaction
from django_filters import CharFilter, DateFromToRangeFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from pydantic import BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.scheduling import SchedulableUserResource, TokenBooking
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    BookingStatusChoices,
    TokenBookingReadSpec,
    TokenBookingWriteSpec,
)
from care.emr.resources.user.spec import UserSpec
from care.facility.models import Facility, FacilityOrganizationUser
from care.security.authorization import AuthorizationController


class CancelBookingSpec(BaseModel):
    reason: Literal[
        BookingStatusChoices.cancelled, BookingStatusChoices.entered_in_error
    ]


class TokenBookingFilters(FilterSet):
    status = CharFilter(field_name="status")
    date = DateFromToRangeFilter(field_name="token_slot__start_datetime__date")
    slot = UUIDFilter(field_name="token_slot__external_id")
    user = UUIDFilter(method="filter_by_user")
    patient = UUIDFilter(field_name="patient__external_id")

    def filter_by_user(self, queryset, name, value):
        if not value:
            return queryset
        resource = SchedulableUserResource.objects.filter(
            user__external_id=value
        ).first()
        if not resource:
            return queryset.none()
        return queryset.filter(token_slot__resource=resource)


class TokenBookingViewSet(
    EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = TokenBooking
    pydantic_model = TokenBookingWriteSpec
    pydantic_read_model = TokenBookingReadSpec
    pydantic_update_model = TokenBookingWriteSpec

    filterset_class = TokenBookingFilters
    filter_backends = [DjangoFilterBackend]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

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
                "token_slot__resource",
                "token_slot__resource__facility",
            )
            .order_by("-modified_date")
        )

    @classmethod
    def cancel_appointment_handler(cls, instance, request_data, user):
        request_data = CancelBookingSpec(**request_data)
        with transaction.atomic():
            if instance.status not in CANCELLED_STATUS_CHOICES:
                # Free up the slot if it is not cancelled already
                instance.token_slot.allocated -= 1
                instance.token_slot.save()
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

    @action(detail=False, methods=["GET"])
    def available_users(self, request, *args, **kwargs):
        facility = Facility.objects.get(external_id=self.kwargs["facility_external_id"])
        facility_users = FacilityOrganizationUser.objects.filter(
            organization__facility=facility,
            user_id__in=SchedulableUserResource.objects.filter(
                facility=facility
            ).values("user_id"),
        )

        return Response(
            {
                "users": [
                    UserSpec.serialize(facility_user.user).to_json()
                    for facility_user in facility_users
                ]
            }
        )
