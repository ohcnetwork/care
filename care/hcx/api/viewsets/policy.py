from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from care.hcx.models.policy import Policy
from care.hcx.api.serializers.policy import PolicySerializer


class PolicyViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet
):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    lookup_field = "external_id"
    search_fields = ["patient"]