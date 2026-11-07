from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.resources.facility_flag.spec import (
    FacilityFlagCreateSpec,
    FacilityFlagReadSpec,
    FacilityFlagRetrieveSpec,
    FacilityFlagUpdateSpec,
)
from care.facility.models import FacilityFlag
from care.security.authorization.base import AuthorizationController
from care.utils.registries.feature_flag import FlagNotFoundError, FlagRegistry, FlagType


class FacilityFlagFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    flag = filters.CharFilter(field_name="flag", lookup_expr="iexact")


class FacilityFlagViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
):
    database_model = FacilityFlag
    pydantic_model = FacilityFlagCreateSpec
    pydantic_update_model = FacilityFlagUpdateSpec
    pydantic_read_model = FacilityFlagReadSpec
    pydantic_retrieve_model = FacilityFlagRetrieveSpec
    filterset_class = FacilityFlagFilters
    filter_backends = [filters.DjangoFilterBackend]

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_facility_flag", self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission to create facility flags"
            )

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_facility_flag", self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission to update facility flags"
            )

    def authorize_destroy(self, instance):
        if not AuthorizationController.call(
            "can_write_facility_flag", self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission to delete facility flags"
            )

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_read_facility_flag", self.request.user
        ):
            raise PermissionDenied("You do not have permission to list facility flags")
        return super().get_queryset()

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            FlagRegistry.register(FlagType.FACILITY, instance.flag)

    def perform_destroy(self, instance):
        with transaction.atomic():
            flag_name = instance.flag
            super().perform_destroy(instance)

            still_used = FacilityFlag.objects.filter(
                flag=flag_name, deleted=False
            ).exists()

            if not still_used:
                FlagRegistry.unregister(FlagType.FACILITY, flag_name)

    @action(detail=False, methods=["GET"], url_path="available-flags")
    def available_flags(self, request):
        if not AuthorizationController.call(
            "can_read_facility_flag", self.request.user
        ):
            raise PermissionDenied("You do not have permission to view available flags")

        try:
            flags = FlagRegistry.get_all_flags(FlagType.FACILITY)
            return Response({"available_flags": list(flags)})
        except FlagNotFoundError:
            return Response(
                {"message": "No registered flag type 'facility' found."}, status=400
            )
