from django_filters import rest_framework as filters
from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers import FacilitySerializer, AmbulanceSerializer
from care.facility.models import Facility, Ambulance


class FacilityBaseViewset(CreateModelMixin, RetrieveModelMixin,
                          UpdateModelMixin, DestroyModelMixin, GenericViewSet):
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


class AmbulanceViewSet(FacilityBaseViewset, ListModelMixin):
    serializer_class = AmbulanceSerializer
    queryset = Ambulance.objects.filter(deleted=False)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('owner_phone_number',)
