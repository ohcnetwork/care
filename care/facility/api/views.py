from django_filters import rest_framework as filters
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers import (
    AmbulanceDriverSerializer,
    AmbulanceSerializer,
    FacilitySerializer,
)
from care.facility.models import Ambulance, Facility


class FacilityBaseViewset(CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """Base class for all endpoints related to Faclity model."""

    permission_classes = (IsAuthenticated,)


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.filter(is_active=True)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return self.queryset.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)


class AmbulanceFilterSet(filters.FilterSet):
    vehicle_numbers = filters.BaseInFilter(field_name="vehicle_number")


class AmbulanceViewSet(FacilityBaseViewset, ListModelMixin):
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
        return Response(data=AmbulanceDriverSerializer(driver).data, status=status.HTTP_201_CREATED)

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

        driver = ambulance.ambulancedriver_set.filter(id=serializer.validated_data["driver_id"]).first()
        if not driver:
            raise serializers.ValidationError({"driver_id": "Detail not found"})

        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
