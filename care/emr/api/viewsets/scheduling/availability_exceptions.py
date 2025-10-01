from django.db import transaction
from django_filters import DateFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpsertMixin,
)
from care.emr.api.viewsets.scheduling.schedule import get_or_create_resource
from care.emr.models import AvailabilityException
from care.emr.models.scheduling.booking import TokenSlot
from care.emr.resources.scheduling.availability_exception.spec import (
    AvailabilityExceptionReadSpec,
    AvailabilityExceptionWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class AvailabilityExceptionFilters(FilterSet):
    user = UUIDFilter(field_name="resource__user__external_id")
    valid_from = DateFilter(field_name="valid_to", lookup_expr="gte")
    valid_to = DateFilter(field_name="valid_from", lookup_expr="lte")


class AvailabilityExceptionsViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    database_model = AvailabilityException
    pydantic_model = AvailabilityExceptionWriteSpec
    pydantic_read_model = AvailabilityExceptionReadSpec
    filterset_class = AvailabilityExceptionFilters
    filter_backends = [DjangoFilterBackend]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def clean_create_data(self, request_data):
        request_data["facility"] = self.kwargs["facility_external_id"]
        return request_data

    def perform_create(self, instance):
        with transaction.atomic():
            resource = get_or_create_resource(
                instance._resource_type,  # noqa SLF001
                instance._resource_id,  # noqa SLF001
                self.get_facility_obj(),
            )
            instance.resource = resource

            slots = TokenSlot.objects.filter(
                resource=resource,
                start_datetime__date__gte=instance.valid_from,
                start_datetime__date__lte=instance.valid_to,
                start_datetime__time__gte=instance.start_time,
                start_datetime__time__lte=instance.end_time,
            )
            if slots.filter(allocated__gt=0).exists():
                raise ValidationError("There are bookings during this exception")
            slots.update(deleted=True)

            super().perform_create(instance)

    def authorize_destroy(self, instance):
        resource_obj = instance.resource
        if not AuthorizationController.call(
            "can_write_schedule", resource_obj, self.request.user
        ):
            raise PermissionDenied("You do not have permission to update schedule")

    def authorize_create(self, instance):
        resource_obj = get_or_create_resource(
            instance.resource_type, instance.resource_id, self.get_facility_obj()
        )
        if not AuthorizationController.call(
            "can_write_schedule",
            resource_obj,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create schedule")

    def authorize_retrieve(self, model_instance):
        if not AuthorizationController.call(
            "can_list_schedule",
            model_instance.resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to update schedule")

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = (
            super()
            .get_queryset()
            .filter(resource__facility=facility)
            .select_related("resource", "created_by", "updated_by")
            .order_by("-modified_date")
        )
        if self.action == "list":
            if (
                "resource_type" not in self.request.query_params
                or "resource_id" not in self.request.query_params
            ):
                raise ValidationError("resource_type and resource_id are required")
            resource_obj = get_or_create_resource(
                self.request.query_params["resource_type"],
                self.request.query_params["resource_id"],
                facility,
            )
            if not AuthorizationController.call(
                "can_list_schedule", resource_obj, self.request.user
            ):
                raise PermissionDenied("You do not have permission to list schedule")
            queryset = queryset.filter(resource=resource_obj)
        return queryset
