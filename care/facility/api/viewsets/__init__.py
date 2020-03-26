from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.mixins import UserAccessMixin


class FacilityBaseViewset(
    UserAccessMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet,
):
    """Base class for all endpoints related to Faclity model."""

    permission_classes = (IsAuthenticated,)
