from django.db import transaction
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.scheduling.schedule import (
    get_or_create_resource,
    validate_resource,
)
from care.emr.models.scheduling.token import TokenSubQueue
from care.emr.resources.scheduling.token_sub_queue.spec import (
    TokenSubQueueBaseSpec,
    TokenSubQueueCreateSpec,
    TokenSubQueueReadSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class TokenSubQueueFilters(FilterSet):
    name = CharFilter(lookup_expr="icontains")
    status = CharFilter(lookup_expr="iexact")


class TokenSubQueueViewSet(EMRModelViewSet):
    database_model = TokenSubQueue
    pydantic_model = TokenSubQueueCreateSpec
    pydantic_update_model = TokenSubQueueBaseSpec
    pydantic_read_model = TokenSubQueueReadSpec
    filterset_class = TokenSubQueueFilters
    filter_backends = [DjangoFilterBackend]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        facility = self.get_facility_obj()
        with transaction.atomic():
            instance.facility = facility
            resource = get_or_create_resource(
                instance._resource_type,  # noqa SLF001
                instance._resource_id,  # noqa SLF001
                facility,
            )
            instance.resource = resource
            super().perform_create(instance)

    def validate_data(self, instance, model_obj=None):
        if not model_obj:
            validate_resource(
                instance.resource_type, instance.resource_id, self.get_facility_obj()
            )

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        resource = get_or_create_resource(
            instance.resource_type, instance.resource_id, facility
        )
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def authorize_update(self, request_obj, model_instance):
        resource = model_instance.resource
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def authorize_destroy(self, instance):
        self.authorize_update({}, instance)

    def clean_create_data(self, request_data):
        request_data["facility"] = self.kwargs["facility_external_id"]
        return request_data

    def can_read_resource_token(self, resource_obj):
        if not AuthorizationController.call(
            "can_list_token",
            resource_obj,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to list token queue")

    def authorize_retrieve(self, model_instance):
        resource_obj = model_instance.resource
        self.can_read_resource_token(resource_obj)

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
                raise ValidationError("resource_type and resource_id is required")
            resource = get_or_create_resource(
                self.request.query_params["resource_type"],
                self.request.query_params.get("resource_id"),
                facility,
            )
            self.can_read_resource_token(resource)
            queryset = queryset.filter(resource=resource)
        return queryset
