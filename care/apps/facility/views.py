from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import permissions

from apps.facility import (
    models as facility_models,
    serializers as facility_serializers
)

class FacilityListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilityListSerializer
    permission_classes = [permissions.AllowAny]
