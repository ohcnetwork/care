from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet


class FacilityBaseViewset(CreateModelMixin, RetrieveModelMixin,
                          UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """Base class for all endpoints related to Faclity model."""

    permission_classes = (IsAuthenticated,)
