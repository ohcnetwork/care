from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin)
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated


from care.facility.models import Facility
from care.facility.api.serializers import FacilitySerializer


class FacilityBaseViewset(CreateModelMixin, RetrieveModelMixin,
                          UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """Base class for all endpoints related to Faclity model."""

    permission_classes = (IsAuthenticated, )


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        return Facility.objects.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)
    