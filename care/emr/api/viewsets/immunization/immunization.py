from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.immunisation import Immunization
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.immunisation.immunization import (
    ImmunizationCreateSpec,
    ImmunizationListSpec,
    ImmunizationRetrieveSpec,
    ImmunizationUpdateSpec,
)


class ImmunizationRecordFilters(filters.FilterSet):
    pass


class ImmunizationRecordViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = Immunization
    pydantic_model = ImmunizationCreateSpec
    pydantic_update_model = ImmunizationUpdateSpec
    pydantic_read_model = ImmunizationListSpec
    pydantic_retrieve_model = ImmunizationRetrieveSpec
    filterset_class = ImmunizationRecordFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]
