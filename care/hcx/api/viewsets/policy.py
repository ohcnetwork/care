from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from care.hcx.models.policy import Policy
from care.hcx.api.serializers.policy import PolicySerializer
from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters


class PolicyFilter(filters.FilterSet):
    patient = filters.UUIDFilter(field_name="patient__external_id")


class PolicyViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    lookup_field = "external_id"
    search_fields = ["patient"]
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    filterset_class = PolicyFilter
