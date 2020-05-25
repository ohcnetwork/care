from rest_framework import viewsets, mixins, permissions, filters as rest_filters

from django_filters import rest_framework as filters

from apps.commons import pagination as commons_pagination
from apps.facility import (
    models as facility_models,
    serializers as facility_serializers,
    filters as facility_filters,
)


class FacilityViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for Faciity list and create
    """

    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilitySerializer
    filter_backends = (
        filters.DjangoFilterBackend,
        rest_filters.OrderingFilter,
    )
    ordering_fields = (
        "total_patient",
        "positive_patient",
        "negative_patient",
    )
    filterset_class = facility_filters.FacilityFilter
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = commons_pagination.CustomPagination


class FacilityUserViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for FacilityUser add and remove
    """

    queryset = facility_models.FacilityUser.objects.all()
    serializer_class = facility_serializers.FacilityUserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class FacilityTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for Faciity type list
    """

    queryset = facility_models.FacilityType.objects.all()
    serializer_class = facility_serializers.FacilityTypeSerializer
    permission_classes = (permissions.IsAuthenticated,)
