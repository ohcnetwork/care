from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer, WardSerializer
from care.users.models import District, LocalBody, State, Ward


class PaginataionOverrideClass(PageNumberPagination):
    page_size = 500


class StateViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = StateSerializer
    queryset = State.objects.all().order_by("id")
    pagination_class = PaginataionOverrideClass

    @action(detail=True, methods=["get"])
    def districts(self, *args, **kwargs):
        state = self.get_object()
        serializer = DistrictSerializer(state.district_set.all().order_by("name"), many=True)
        return Response(data=serializer.data)


class DistrictFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="state_id")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")
    district_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class DistrictViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = DistrictSerializer
    queryset = District.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DistrictFilterSet
    pagination_class = PaginataionOverrideClass

    @action(detail=True, methods=["get"])
    def local_bodies(self, *args, **kwargs):
        district = self.get_object()
        serializer = LocalBodySerializer(district.localbody_set.all().order_by("name"), many=True)
        return Response(data=serializer.data)

    @method_decorator(cache_page(3600))
    @action(detail=True, methods=["get"])
    def get_all_local_body(self, *args, **kwargs):
        district = self.get_object()
        data = []
        for lsg_object in LocalBody.objects.filter(district=district):
            local_body_object = LocalBodySerializer(lsg_object).data
            local_body_object["wards"] = WardSerializer(Ward.objects.filter(local_body=lsg_object), many=True).data
            data.append(local_body_object)
        return Response(data)


class LocalBodyFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="district__state_id")
    state_name = filters.CharFilter(field_name="district__state__name", lookup_expr="icontains")
    district = filters.NumberFilter(field_name="district_id")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")
    local_body_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class LocalBodyViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = LocalBodySerializer
    queryset = LocalBody.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = LocalBodyFilterSet
    pagination_class = PaginataionOverrideClass


class WardFilterSet(filters.FilterSet):
    state = filters.NumberFilter(field_name="district__state_id")
    state_name = filters.CharFilter(field_name="district__state__name", lookup_expr="icontains")
    district = filters.NumberFilter(field_name="local_body__district_id")
    district_name = filters.CharFilter(field_name="local_body__district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="local_body_id")
    local_body_name = filters.CharFilter(field_name="local_body__name", lookup_expr="icontains")
    ward_name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class WardViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = WardSerializer
    queryset = Ward.objects.all().order_by("name")
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = WardFilterSet
    pagination_class = PaginataionOverrideClass

