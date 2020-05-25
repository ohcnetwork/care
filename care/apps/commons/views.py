from rest_framework import (
    mixins as rest_mixins,
    permissions as rest_permissions,
    viewsets as rest_viewsets,
)

from apps.commons import (
    models as commons_models,
    serializers as commons_serializers,
)


class OwnershiptTypeViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    ViewSet for Ownership Type List
    """

    queryset = commons_models.OwnershipType.objects.all()
    serializer_class = commons_serializers.OwnershipTypeSerializer
    permission_classes = (rest_permissions.IsAuthenticated,)
