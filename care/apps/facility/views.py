from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework import permissions

from apps.facility import (
    models as facility_models,
    serializers as facility_serializers
)

class FacilityListView(ReadOnlyModelViewSet):

    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilityListSerializer
    permission_classes = [permissions.AllowAny]
