from django_filters import rest_framework as filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.testing_lab import TestingLabSerializer
from care.facility.models.testing_lab import TestingLab


class TestingLabFilterSet(filters.FilterSet):
    name = filters.BaseInFilter(field_name="name")
    pincode = filters.BaseInFilter(field_name="pincode")

    local_body = filters.CharFilter(field_name="local_body_id")
    district = filters.CharFilter(field_name="district_id")
    state = filters.CharFilter(field_name="state_id")

    local_body_name = filters.CharFilter(field_name="local_body__name", lookup_expr="icontains")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")


class TestingLabViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = TestingLabSerializer
    queryset = TestingLab.objects.all().select_related("local_body", "district", "state")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = TestingLabFilterSet
