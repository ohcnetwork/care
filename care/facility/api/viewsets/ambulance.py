from django_filters import rest_framework as filters
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from care.facility.api.serializers.ambulance import (
    AmbulanceSerializer,
    AmbulanceDriverSerializer,
)
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Ambulance

from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
)
from rest_framework.viewsets import GenericViewSet


class AmbulanceFilterSet(filters.FilterSet):
    vehicle_numbers = filters.BaseInFilter(field_name="vehicle_number")


class AmbulanceViewSet(FacilityBaseViewset, ListModelMixin):
    permission_classes = (AllowAny,)
    serializer_class = AmbulanceSerializer
    queryset = Ambulance.objects.filter(deleted=False)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AmbulanceFilterSet

    @action(methods=["POST"], detail=True)
    def add_driver(self, request):
        ambulance = self.get_object()
        serializer = AmbulanceDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = ambulance.ambulancedriver_set.create(**serializer.validated_data)
        return Response(
            data=AmbulanceDriverSerializer(driver).data, status=status.HTTP_201_CREATED
        )

    @action(methods=["DELETE"], detail=True)
    def remove_driver(self, request):
        class DeleteDriverSerializer(serializers.Serializer):
            driver_id = serializers.IntegerField()

            def update(self, instance, validated_data):
                raise NotImplementedError

            def create(self, validated_data):
                raise NotImplementedError

        ambulance = self.get_object()
        serializer = DeleteDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = ambulance.ambulancedriver_set.filter(
            id=serializer.validated_data["driver_id"]
        ).first()
        if not driver:
            raise serializers.ValidationError({"driver_id": "Detail not found"})

        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AmbulanceCreateViewSet(CreateModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = AmbulanceSerializer
    queryset = Ambulance.objects.filter(deleted=False)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AmbulanceFilterSet
