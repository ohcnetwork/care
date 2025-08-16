from django.shortcuts import get_object_or_404
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
from care.emr.models.tag_config import TagConfig
from care.emr.resources.tag.config_spec import (
    TagConfigReadSpec,
    TagConfigRetrieveSpec,
    TagConfigUpdateSpec,
    TagConfigWriteSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter


class TagConfigFilters(filters.FilterSet):
    facility = filters.UUIDFilter(
        lookup_expr="exact", field_name="facility__external_id"
    )
    facility_organization = filters.UUIDFilter(
        lookup_expr="exact", field_name="facility_organization__external_id"
    )
    organization = filters.UUIDFilter(
        lookup_expr="exact", field_name="organization__external_id"
    )
    slug = filters.CharFilter(lookup_expr="icontains")
    status = filters.CharFilter(lookup_expr="iexact")
    display = filters.CharFilter(lookup_expr="icontains")
    category = filters.CharFilter(lookup_expr="iexact")
    parent = filters.UUIDFilter(lookup_expr="exact", field_name="parent__external_id")
    resource = filters.CharFilter(lookup_expr="iexact")
    parent_is_null = NullFilter(field_name="parent")
    ids = MultiSelectFilter(field_name="external_id")


class TagConfigViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = TagConfig
    pydantic_model = TagConfigWriteSpec
    pydantic_update_model = TagConfigUpdateSpec
    pydantic_read_model = TagConfigReadSpec
    pydantic_retrieve_model = TagConfigRetrieveSpec
    filterset_class = TagConfigFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["priority", "created_date", "modified_date"]

    def authorize_retrieve(self, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_list_facility_tag_config", self.request.user, model_instance.facility
        ):
            raise PermissionDenied("You do not have permission to read tag configs")

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility and not AuthorizationController.call(
            "can_write_facility_tag_config", self.request.user, model_instance.facility
        ):
            raise PermissionDenied("You do not have permission to write tag configs")
        if not model_instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("You do not have permission to write tag configs")

    def authorize_create(self, instance):
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_tag_config", self.request.user, facility
            ):
                raise PermissionDenied(
                    "You do not have permission to write tag configs"
                )
        if not instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied("You do not have permission to write tag configs")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            if "facility" in self.request.GET:
                facility = get_object_or_404(
                    Facility, external_id=self.request.GET["facility"]
                )
                if not AuthorizationController.call(
                    "can_list_facility_tag_config", self.request.user, facility
                ):
                    raise PermissionDenied(
                        "You do not have permission to read tag configs"
                    )
                queryset = queryset.filter(facility=facility)
            else:
                queryset = queryset.filter(facility__isnull=True)
        return queryset
