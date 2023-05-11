from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.hcx.api.serializers.communication import CommunicationSerializer
from care.hcx.models.communication import Communication


class CommunicationFilter(filters.FilterSet):
    claim = filters.UUIDFilter(field_name="claim__external_id")


class CommunicationViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = Communication.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = CommunicationSerializer
    lookup_field = "external_id"
    search_fields = ["claim"]
    filter_backends = (
        filters.DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    filterset_class = CommunicationFilter
    ordering_fields = [
        "id",
        "created_date",
        "modified_date",
    ]
