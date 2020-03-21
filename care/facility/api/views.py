from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    DestroyModelMixin)
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated


from care.facility.models import Facility
from care.facility.api.serializer import FacilitySerializer


class FacilityBaseViewset(CreateModelMixin, RetrieveModelMixin,
                   UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """Base class for all endpoints related to Faclity model."""

    permission_classes = (IsAuthenticated, )


class FacilityViewSet(FacilityBaseViewset, ListModelMixin):
    """Viewset for facility CRUD operations."""

    serializer_class = FacilitySerializer
    queryset = Facility.objects.all()
