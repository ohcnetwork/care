from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.ambulance import (
    AmbulanceDriverSerializer,
    AmbulanceSerializer,
    DeleteDriverSerializer,
)
from care.facility.api.viewsets import UserAccessMixin
from care.facility.models.ambulance import Ambulance


class AmbulanceFilterSet(filters.FilterSet):
    vehicle_numbers = filters.BaseInFilter(field_name="vehicle_number")

    primary_district = filters.CharFilter(field_name="primary_district_id")
    secondary_district = filters.CharFilter(field_name="secondary_district_id")
    third_district = filters.CharFilter(field_name="third_district_id")

    primary_district_name = filters.CharFilter(
        field_name="primary_district__name", lookup_expr="icontains"
    )
    secondary_district_name = filters.CharFilter(
        field_name="secondary_district__name", lookup_expr="icontains"
    )
    third_district_name = filters.CharFilter(
        field_name="third_district__name", lookup_expr="icontains"
    )


class AmbulanceViewSet(
    UserAccessMixin,
    RetrieveModelMixin,
    ListModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = AmbulanceSerializer
    queryset = Ambulance.objects.filter(deleted=False).select_related(
        "primary_district", "secondary_district", "third_district"
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AmbulanceFilterSet

    def get_serializer_class(self):
        if self.action == "add_driver":
            return AmbulanceDriverSerializer
        if self.action == "remove_driver":
            return DeleteDriverSerializer
        return AmbulanceSerializer

    @extend_schema(tags=["ambulance"])
    @action(methods=["POST"], detail=True)
    def add_driver(self, request, *args, **kwargs):
        ambulance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = ambulance.ambulancedriver_set.create(**serializer.validated_data)
        return Response(
            data=AmbulanceDriverSerializer(driver).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(tags=["ambulance"])
    @action(methods=["DELETE"], detail=True)
    def remove_driver(self, request, *args, **kwargs):
        ambulance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = ambulance.ambulancedriver_set.filter(
            id=serializer.validated_data["driver_id"]
        ).first()
        if not driver:
            raise serializers.ValidationError({"driver_id": "Detail not found"})

        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
