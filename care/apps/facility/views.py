from rest_framework import viewsets, mixins, permissions

from django_filters import rest_framework as filters

from apps.commons import (
    constants as commons_constants,
    pagination as commons_pagination,
)
from apps.facility import (
    models as facility_models,
    serializers as facility_serializers,
    filters as facility_filters,
)


class FacilityViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for Facility list and create
    """

    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilitySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        filter_kwargs = {}
        if self.request.user.user_type:
            if self.request.user.user_type.name == commons_constants.FACILITY_USER:
                filter_kwargs["facilityuser__user"] = self.request.user
            elif self.request.user.user_type.name == commons_constants.PORTEA:
                filter_kwargs["id__in"] = []
        return facility_models.Facility.objects.filter(**filter_kwargs)


class FacilityUserViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for FacilityUser add and remove
    """

    queryset = facility_models.FacilityUser.objects.all()
    serializer_class = facility_serializers.FacilityUserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class InventorySerializerViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for Inventory add, list and update
    """

    queryset = facility_models.Inventory.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = facility_filters.InventoryFilter
    serializer_class = facility_serializers.InventorySerializer
    pagination_class = commons_pagination.CustomPagination
