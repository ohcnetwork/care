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

from care.hcx.api.serializers.policy import PolicySerializer
from care.hcx.models.policy import Policy
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


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
    permission_classes = (IsAuthenticated,)
    serializer_class = PolicySerializer
    lookup_field = "external_id"
    search_fields = ["patient"]
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

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(patient__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(patient__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(patient__facility__id__in=allowed_facilities)

        return queryset
