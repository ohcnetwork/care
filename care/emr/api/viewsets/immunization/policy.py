from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.immunisation import ImmunizationPolicy
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.immunisation.policy import (
    ImmunizationPolicyCreateSpec,
    ImmunizationPolicyListSpec,
    ImmunizationPolicyRetrieveSpec,
    ImmunizationPolicyUpdateSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyUUIDFilter
from care.utils.shortcuts import get_object_or_404


class ImmunizationPolicyFilters(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    facility = DummyUUIDFilter()


class ImmunizationPolicyViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = ImmunizationPolicy
    pydantic_model = ImmunizationPolicyCreateSpec
    pydantic_update_model = ImmunizationPolicyUpdateSpec
    pydantic_read_model = ImmunizationPolicyListSpec
    pydantic_retrieve_model = ImmunizationPolicyRetrieveSpec
    filterset_class = ImmunizationPolicyFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]

    def authorize_create(self, instance):
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_immunization_policy",
                self.request.user,
                facility,
            ):
                raise PermissionDenied("Access Denied to Immunization Policy")
        elif not self.request.user.is_superuser:
            raise PermissionDenied("Access Denied to Immunization Policy")
        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility:
            if not AuthorizationController.call(
                "can_write_facility_immunization_policy",
                self.request.user,
                model_instance.facility,
            ):
                raise PermissionDenied("Access Denied to Immunization Policy")
        elif not self.request.user.is_superuser:
            raise PermissionDenied("Access Denied to Immunization Policy")
        return super().authorize_update(request_obj, model_instance)

    def authorize_retrieve(self, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_list_facility_immunization_policy",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Immunization Policy")
        return super().authorize_retrieve(model_instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            if "facility" in self.request.GET:
                facility = get_object_or_404(
                    Facility, external_id=self.request.GET["facility"]
                )
                # Authorize Facility
                if not AuthorizationController.call(
                    "can_list_facility_immunization_policy",
                    self.request.user,
                    facility,
                ):
                    raise PermissionDenied("Access Denied to Immunization Policy")
                queryset = queryset.filter(
                    Q(facility=facility) | Q(facility__isnull=True)
                )
            else:
                queryset = queryset.filter(facility__isnull=True)
        return queryset
