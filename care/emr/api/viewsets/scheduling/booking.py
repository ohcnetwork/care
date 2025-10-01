from typing import Literal

from django.db import transaction
from django_filters import DateFromToRangeFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework import filters as rest_framework_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRTagMixin,
    EMRUpdateMixin,
)
from care.emr.api.viewsets.scheduling import lock_create_appointment
from care.emr.api.viewsets.scheduling.schedule import get_or_create_resource
from care.emr.models import TokenSlot
from care.emr.models.organization import (
    FacilityOrganization,
    FacilityOrganizationUser,
    OrganizationUser,
)
from care.emr.models.scheduling import SchedulableResource, TokenBooking
from care.emr.models.scheduling.token import Token, TokenCategory, TokenQueue
from care.emr.resources.charge_item.handle_charge_item_cancel import (
    handle_charge_item_cancel,
)
from care.emr.resources.charge_item.spec import ChargeItemStatusOptions
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.emr.resources.scheduling.slot.spec import (
    CANCELLED_STATUS_CHOICES,
    BookingStatusChoices,
    TokenBookingReadSpec,
    TokenBookingRetrieveSpec,
    TokenBookingWriteSpec,
)
from care.emr.resources.scheduling.token.spec import TokenReadSpec, TokenStatusOptions
from care.emr.resources.tag.config_spec import TagResource
from care.emr.resources.user.spec import UserSpec
from care.emr.tagging.base import SingleFacilityTagManager
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.utils.filters.dummy_filter import DummyCharFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.lock import Lock
from care.utils.shortcuts import get_object_or_404


class CancelBookingSpec(BaseModel):
    reason: Literal[
        BookingStatusChoices.cancelled,
        BookingStatusChoices.entered_in_error,
        BookingStatusChoices.rescheduled,
    ]
    note: str | None = None


class TokenGenerationSpec(BaseModel):
    category: UUID4
    note: str | None = None
    queue: UUID4 | None = None


class RescheduleBookingSpec(BaseModel):
    new_slot: UUID4
    new_booking_note: str
    previous_booking_note: str | None = None

    tags: list[UUID4] = []


class TokenBookingFilters(FilterSet):
    status = MultiSelectFilter(field_name="status")
    date = DateFromToRangeFilter(field_name="token_slot__start_datetime__date")
    slot = UUIDFilter(field_name="token_slot__external_id")
    resource_type = DummyCharFilter()
    resource_ids = DummyCharFilter()
    patient = UUIDFilter(field_name="patient__external_id")


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
    pydantic_retrieve_model = TokenBookingRetrieveSpec
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
        resource = model_instance.token_slot.resource
        if not AuthorizationController.call(
            "can_write_booking",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to update bookings")

    def authorize_retrieve(self, model_instance):
        resource = model_instance.token_slot.resource
        if not AuthorizationController.call(
            "can_list_booking",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to retrieve bookings")

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = (
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
        if self.action == "list":
            if "resource_type" not in self.request.query_params:
                raise ValidationError("Resource Type is required")

            organization_ids = []
            if self.request.query_params.get("organization_ids"):
                organization_ids = self.request.query_params.get(
                    "organization_ids", ""
                ).split(",")
            resource_ids = []
            if self.request.query_params.get("resource_ids"):
                resource_ids = self.request.query_params.get("resource_ids", "").split(
                    ","
                )

            queryset = authorize_booking_list(
                queryset,
                self.request.query_params["resource_type"],
                organization_ids,
                resource_ids,
                self.request.user,
                facility,
            )
        return queryset

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
            if instance.charge_item:
                handle_charge_item_cancel(instance.charge_item)
                instance.charge_item.status = ChargeItemStatusOptions.aborted.value
                instance.charge_item.save()
            instance.save()
        return Response(
            TokenBookingReadSpec.serialize(instance).model_dump(exclude=["meta"])
        )

    @action(detail=True, methods=["POST"])
    def cancel(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        return self.cancel_appointment_handler(instance, request.data, request.user)

    @extend_schema(
        request=RescheduleBookingSpec,
    )
    @action(detail=True, methods=["POST"])
    def reschedule(self, request, *args, **kwargs):
        request_data = RescheduleBookingSpec(**request.data)
        existing_booking = self.get_object()
        facility = self.get_facility_obj()
        self.authorize_update({}, existing_booking)
        if not AuthorizationController.call(
            "can_reschedule_booking", self.request.user, facility
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
        user_resources = SchedulableResource.objects.filter(
            facility=facility,
            user__deleted=False,
        )
        if request.query_params.get("organization_ids"):
            organization_ids = request.query_params.get("organization_ids").split(",")
            organizations = FacilityOrganization.objects.filter(
                external_id__in=organization_ids, facility=facility
            )
            facility_organization_users = FacilityOrganizationUser.objects.filter(
                organization__in=organizations
            )
            user_resources = user_resources.filter(
                user_id__in=facility_organization_users.values("user_id")
            )

        return Response(
            {
                "users": [
                    UserSpec.serialize(user_resource.user).to_json()
                    for user_resource in user_resources
                ]
            }
        )

    @extend_schema(
        request=TokenGenerationSpec,
    )
    @action(detail=True, methods=["POST"])
    def generate_token(self, request, *args, **kwargs):
        booking = self.get_object()
        self.authorize_update({}, booking)
        request_data = TokenGenerationSpec(**request.data)
        if booking.token:
            raise ValidationError("Token already generated")
        filters = {
            "facility": booking.token_slot.resource.facility,
            "resource": booking.token_slot.resource,
            "date": booking.token_slot.start_datetime.date(),
        }
        if request_data.queue:
            queue = TokenQueue.objects.filter(
                external_id=request_data.queue, **filters
            ).first()
            if not queue:
                raise ValidationError("Queue not found")
        else:
            queue_exists = TokenQueue.objects.filter(**filters).exists()
            filters["system_generated"] = True
            queue = TokenQueue.objects.filter(**filters).first()
            if not queue:
                filters["name"] = "System Generated"
                if not queue_exists:
                    filters["is_primary"] = True
                queue = TokenQueue.objects.create(**filters)
        category = TokenCategory.objects.filter(
            facility=booking.token_slot.resource.facility,
            resource_type=booking.token_slot.resource.resource_type,
            external_id=request_data.category,
        ).first()
        if not category:
            raise ValidationError("Category not found")
        note = request_data.note
        with Lock(f"booking:token:{queue.id}"), transaction.atomic():
            number = Token.objects.filter(queue=queue, category=category).count() + 1
            token = Token.objects.create(
                facility=booking.token_slot.resource.facility,
                queue=queue,
                category=category,
                number=number,
                status=TokenStatusOptions.CREATED.value,
                note=note,
                booking=booking,
                patient=booking.patient,
            )
            booking.token = token
            booking.save(update_fields=["token"])
        return Response(TokenReadSpec.serialize(token).to_json())


def authorize_booking_list(
    base_query, resource_type, organization_ids, resource_ids, user, facility
):
    if resource_type == SchedulableResourceTypeOptions.practitioner.value:
        if organization_ids:
            organizations = FacilityOrganization.objects.filter(
                external_id__in=organization_ids, facility=facility
            )
            if organizations.count() != len(organization_ids):
                raise PermissionDenied("Invalid organization ids")
            for organization in organizations:
                if not AuthorizationController.call(
                    "can_list_booking_organization",
                    organization,
                    user,
                    facility,
                ):
                    raise PermissionDenied(
                        "You do not have permission to list bookings"
                    )
                users = OrganizationUser.objects.filter(
                    organization=organization
                ).values("user_id")
                # TODO : Change to overlap to include children as well
                base_query = base_query.filter(
                    token_slot__resource__in=SchedulableResource.objects.filter(
                        user__in=users, facility=facility
                    )
                )
        if not resource_ids and not organization_ids and not user.is_superuser:
            raise PermissionDenied("You do not have permission to list bookings")
    elif resource_type in [
        SchedulableResourceTypeOptions.healthcare_service.value,
        SchedulableResourceTypeOptions.location.value,
    ]:
        if not resource_ids:
            raise PermissionDenied("You do not have permission to list bookings")
    else:
        raise ValidationError("Invalid resource type")
    if resource_ids:
        resource_pk_ids = []
        for resource_id in resource_ids:
            resource = get_or_create_resource(resource_type, resource_id, facility)
            if not AuthorizationController.call("can_list_booking", resource, user):
                raise PermissionDenied("You do not have permission to list bookings")
            resource_pk_ids.append(resource.id)
        base_query = base_query.filter(token_slot__resource_id__in=resource_pk_ids)
    return base_query
