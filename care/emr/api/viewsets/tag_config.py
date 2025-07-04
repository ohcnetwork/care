from django_filters import rest_framework as filters

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


class TagConfigViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = TagConfig
    pydantic_model = TagConfigWriteSpec
    pydantic_update_model = TagConfigUpdateSpec
    pydantic_read_model = TagConfigReadSpec
    pydantic_retrieve_model = TagConfigRetrieveSpec
    # TODO AuthZ for Retrieve and Update
    filterset_class = TagConfigFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.GET.get("facility"):
            queryset = queryset.filter(facility__isnull=True)
        return queryset

    # TODO : AuthZ
