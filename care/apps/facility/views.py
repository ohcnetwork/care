from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.facility import (
    models as facility_models,
    serializers as facility_serializers
)

class FacilityListView(generics.ListAPIView):
    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilityListSerializer
    permission_classes = [AllowAny]
