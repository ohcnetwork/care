from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from care.hcx.models.claim import Claim
from care.hcx.api.serializers.claim import ClaimSerializer


class ClaimViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = Claim.objects.all()
    serializer_class = ClaimSerializer
    lookup_field = "external_id"
    search_fields = ["consultation", "policy"]
