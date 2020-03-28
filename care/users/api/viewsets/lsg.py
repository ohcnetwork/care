from django_filters import rest_framework as filters
from rest_framework import viewsets

from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
)
from care.users.models import District, LocalBody, State


class StateViewSet(viewsets.ModelViewSet):
    serializer_class = StateSerializer
    queryset = State.objects.all()
    http_method_names = ["get"]  # allows only reads


class DistrictFilterSet(filters.FilterSet):
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")


class DistrictViewSet(viewsets.ModelViewSet):
    serializer_class = DistrictSerializer
    queryset = District.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DistrictFilterSet
    http_method_names = ["get"]  # allows only reads


class LocalBodyFilterSet(filters.FilterSet):
    state_name = filters.CharFilter(field_name="district__state__name", lookup_expr="icontains")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")


class LocalBodyViewSet(viewsets.ModelViewSet):
    serializer_class = LocalBodySerializer
    queryset = LocalBody.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = LocalBodyFilterSet
    http_method_names = ["get"]  # allows only reads
