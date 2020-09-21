from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer, WardSerializer
from care.users.models import District, LocalBody, State, Ward


class StateViewSet(viewsets.ModelViewSet):
    serializer_class = StateSerializer
    queryset = State.objects.all().order_by("name")
    http_method_names = ["get"]  # allows only reads

    @action(detail=True, methods=["get"])
    def districts(self, *args, **kwargs):
        state = self.get_object()
        serializer = DistrictSerializer(state.district_set.all().order_by("name"), many=True)
        return Response(data=serializer.data)


class DistrictFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="state_id")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")
    district_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class DistrictViewSet(viewsets.ModelViewSet):
    serializer_class = DistrictSerializer
    queryset = District.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DistrictFilterSet
    http_method_names = ["get"]  # allows only reads

    @action(detail=True, methods=["get"])
    def local_bodies(self, *args, **kwargs):
        district = self.get_object()
        serializer = LocalBodySerializer(district.localbody_set.all().order_by("name"), many=True)
        return Response(data=serializer.data)


class LocalBodyFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="district__state_id")
    state_name = filters.CharFilter(field_name="district__state__name", lookup_expr="icontains")
    district = filters.NumberFilter(field_name="district_id")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")
    local_body_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class LocalBodyViewSet(viewsets.ModelViewSet):
    serializer_class = LocalBodySerializer
    queryset = LocalBody.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = LocalBodyFilterSet
    http_method_names = ["get"]  # allows only reads


class WardFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="district__state_id")
    state_name = filters.CharFilter(field_name="district__state__name", lookup_expr="icontains")
    district = filters.NumberFilter(field_name="local_body__district_id")
    district_name = filters.CharFilter(field_name="local_body__district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="local_body_id")
    local_body_name = filters.CharFilter(field_name="local_body__name", lookup_expr="icontains")
    ward_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class WardViewSet(viewsets.ModelViewSet):
    serializer_class = WardSerializer
    queryset = Ward.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = WardFilterSet
    http_method_names = ["get"]  # allows only reads
