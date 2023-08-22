from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.health_facility import HealthFacilitySerializer
from care.abdm.models import HealthFacility


class HealthFacilityViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    serializer_class = HealthFacilitySerializer
    model = HealthFacility
    queryset = HealthFacility.objects.all()
    permission_classes = (IsAuthenticated,)
    lookup_field = "facility__external_id"
