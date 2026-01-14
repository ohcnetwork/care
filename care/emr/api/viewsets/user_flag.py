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
from care.emr.resources.user_flag.spec import (
    UserFlagCreateSpec,
    UserFlagReadSpec,
    UserFlagRetrieveSpec,
    UserFlagUpdateSpec,
)
from care.security.authorization.base import AuthorizationController
from care.users.models import UserFlag
from care.utils.registries.feature_flag import FlagNotFoundError, FlagRegistry, FlagType


class UserFlagFilters(filters.FilterSet):
    user = filters.UUIDFilter(field_name="user__external_id")
    flag = filters.CharFilter(field_name="flag", lookup_expr="iexact")


class UserFlagViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
):
    database_model = UserFlag
    pydantic_model = UserFlagCreateSpec
    pydantic_update_model = UserFlagUpdateSpec
    pydantic_read_model = UserFlagReadSpec
    pydantic_retrieve_model = UserFlagRetrieveSpec
    filterset_class = UserFlagFilters
    filter_backends = [filters.DjangoFilterBackend]

    def authorize_create(self, instance):
        if not AuthorizationController.call("can_write_user_flag", self.request.user):
            raise PermissionDenied("You do not have permission to create user flags")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call("can_write_user_flag", self.request.user):
            raise PermissionDenied("You do not have permission to update user flags")

    def authorize_destroy(self, instance):
        if not AuthorizationController.call("can_write_user_flag", self.request.user):
            raise PermissionDenied("You do not have permission to delete user flags")

    def get_queryset(self):
        if not AuthorizationController.call("can_read_user_flag", self.request.user):
            raise PermissionDenied("You do not have permission to list user flags")
        return super().get_queryset()

    def perform_create(self, instance):
        with transaction.atomic():
            FlagRegistry.register(FlagType.USER, instance.flag)
            super().perform_create(instance)

    def perform_destroy(self, instance):
        with transaction.atomic():
            super().perform_destroy(instance)
            FlagRegistry.unregister(FlagType.USER, instance.flag)

    @action(detail=False, methods=["GET"], url_path="available-flags")
    def available_flags(self, request):
        if not AuthorizationController.call("can_read_user_flag", self.request.user):
            raise PermissionDenied("You do not have permission to view available flags")
        try:
            flags = FlagRegistry.get_all_flags(FlagType.USER)
            return Response({"available_flags": list(flags)})
        except FlagNotFoundError:
            return Response(
                {"message": "No registered flag type 'user' found."}, status=400
            )
