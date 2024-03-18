from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.hcx.api.serializers.claim import ClaimSerializer
from care.hcx.models.base import UseEnum
from care.hcx.models.claim import Claim
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class PolicyFilter(filters.FilterSet):
    consultation = filters.UUIDFilter(field_name="consultation__external_id")
    policy = filters.UUIDFilter(field_name="policy__external_id")
    use = filters.ChoiceFilter(field_name="use", choices=UseEnum.choices)


class ClaimViewSet(
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = Claim.objects.all().select_related(
        "policy", "created_by", "last_modified_by"
    )
    permission_classes = (IsAuthenticated,)
    serializer_class = ClaimSerializer
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

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(consultation__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(consultation__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(
                consultation__facility__id__in=allowed_facilities
            )

        return queryset
