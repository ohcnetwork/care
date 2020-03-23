from rest_framework.mixins import ListModelMixin

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility


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
