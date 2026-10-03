from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.immunisation import ImmunizationRecommendation
from care.emr.resources.favorites.filters import FavoritesFilter
from care.emr.resources.immunisation.recommendation import (
    ImmunizationRecommendationCreateSpec,
    ImmunizationRecommendationListSpec,
    ImmunizationRecommendationRetrieveSpec,
    ImmunizationRecommendationUpdateSpec,
)


class ImmunizationReccomendationFilters(filters.FilterSet):
    pass


class ImmunizationRecommendationViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = ImmunizationRecommendation
    pydantic_model = ImmunizationRecommendationCreateSpec
    pydantic_update_model = ImmunizationRecommendationUpdateSpec
    pydantic_read_model = ImmunizationRecommendationListSpec
    pydantic_retrieve_model = ImmunizationRecommendationRetrieveSpec
    filterset_class = ImmunizationReccomendationFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter, FavoritesFilter]
    ordering_fields = ["created_date", "modified_date"]
