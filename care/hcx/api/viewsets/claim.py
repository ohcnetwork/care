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

from care.hcx.api.serializers.claim import ClaimDetailSerializer, ClaimListSerializer
from care.hcx.models.base import USE_CHOICES
from care.hcx.models.claim import Claim


class PolicyFilter(filters.FilterSet):
    consultation = filters.UUIDFilter(field_name="consultation__external_id")
    policy = filters.UUIDFilter(field_name="policy__external_id")
    use = filters.ChoiceFilter(field_name="use", choices=USE_CHOICES)


class ClaimViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = Claim.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ClaimDetailSerializer
    lookup_field = "external_id"
    search_fields = ["consultation", "policy"]
    filter_backends = (
        filters.DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    filterset_class = PolicyFilter
    ordering_fields = [
        "id",
        "created_date",
        "modified_date",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ClaimListSerializer
        return self.serializer_class
