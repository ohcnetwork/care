from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.facility.api.serializers.appointment import (
    AppointmentBookingReadOnlySerializer,
    AppointmentBookingSerializer,
    AvailableDoctorsSerializer,
    DateRangeQuerySerializer,
    DateTimeRangeQuerySerializer,
    TokenSlotReadOnlySerializer,
)
from care.facility.models.appointment import TokenBooking
from care.facility.models.schedule import (
    RESOURCE_TO_MODEL,
    SchedulableResource,
    ScheduleResourceType,
    SlotType,
)
from care.facility.svc.schedule import book_slot, get_appointment_slots_for_resource
from care.users.models import User

RESOURCE_FILTER_KEYS = {
    "doctor_username": {
        "model": RESOURCE_TO_MODEL[ScheduleResourceType.DOCTOR],
        "lookup_field": "username",
    },
}


class AppointmentFilterSet(filters.FilterSet):
    date_from = filters.DateFilter(field_name="valid_from", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="valid_to", lookup_expr="lte")


class AppointmentDRYFilterSet(DRYPermissionFiltersBase):
    def filter_list_queryset(self, request, queryset, view):
        if request.user.is_superuser:
            pass
        elif request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(resource__facility__state=request.user.state)
        elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                resource__facility__district=request.user.district
            )
        else:
            queryset = queryset.filter(
                resource__facility__users__id__exact=request.user.id
            )

        for key, model in RESOURCE_FILTER_KEYS.items():
            value = request.query_params.get(key)
            if value:
                lookup_model = model["model"]
                resource = lookup_model.objects.get(**{model["lookup_field"]: value})
                return queryset.filter(
                    resource__resource_id=resource.id,
                    resource__resource_type=ContentType.objects.get_for_model(
                        lookup_model
                    ),
                )

        return queryset.none()


class AppointmentViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin
):
    queryset = TokenBooking.objects.all()
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "external_id"
    serializer_class = AppointmentBookingReadOnlySerializer

    def get_serializer_class(self):
        if self.action == "available_doctors":
            return AvailableDoctorsSerializer
        return super().get_serializer_class()

    def _get_resource(self, request) -> any:
        for key, model in RESOURCE_FILTER_KEYS.items():
            value = request.query_params.get(key) or request.data.get(key)
            if value:
                lookup_model = model["model"]
                resource = lookup_model.objects.get(**{model["lookup_field"]: value})
                return SchedulableResource.objects.get(
                    resource_id=resource.id,
                    resource_type=ContentType.objects.get_for_model(lookup_model),
                )
        msg = "Resource not found"
        raise ObjectDoesNotExist(msg)

    @action(detail=False, methods=["get"])
    def available_doctors(self, request, *args, **kwargs):
        serializer = DateRangeQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        schedulable_doctor_resources = SchedulableResource.objects.filter(
            resource_type=ContentType.objects.get_for_model(User),
            resource_id__in=User.objects.filter(
                user_type__in=[
                    User.TYPE_VALUE_MAP["Doctor"],
                    User.TYPE_VALUE_MAP["Nurse"],
                ]
            ),
            schedule__valid_from__lte=serializer.validated_data["valid_to"],
            schedule__valid_to__gte=serializer.validated_data["valid_from"],
        )

        pagainated_queryset = self.paginate_queryset(schedulable_doctor_resources)
        serializer = AvailableDoctorsSerializer(pagainated_queryset, many=True)

        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"])
    def slots(self, *args, **kwargs):
        try:
            resource = self._get_resource(self.request)
        except ObjectDoesNotExist:
            return Response({"detail": "Resource not found"}, status=404)

        serializer = DateTimeRangeQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)

        slots = get_appointment_slots_for_resource(
            resource=resource,
            from_datetime=serializer.validated_data["valid_from"],
            to_datetime=serializer.validated_data["valid_to"],
        )
        serializer = TokenSlotReadOnlySerializer(slots, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        try:
            resource = self._get_resource(request)
        except ObjectDoesNotExist:
            return Response({"detail": "Resource not found"}, status=404)

        serializer = AppointmentBookingSerializer(
            data={**request.data, "resource": resource.external_id}
        )
        serializer.is_valid(raise_exception=True)

        booking = book_slot(
            booked_by=request.user,
            patient=serializer.validated_data["patient"],
            resource=resource,
            slot_type=SlotType.APPOINTMENT,
            slot_start=serializer.validated_data["slot_start"],
            reason_for_visit=serializer.validated_data["reason_for_visit"],
        )
        serializer = AppointmentBookingReadOnlySerializer(booking)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
