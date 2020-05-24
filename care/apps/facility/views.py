from rest_framework import viewsets, mixins, permissions

from apps.facility import models as facility_models, serializers as facility_serializers


class FacilityViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for Faciity list and create
    """

    queryset = facility_models.Facility.objects.all()
    serializer_class = facility_serializers.FacilitySerializer
    permission_classes = (permissions.IsAuthenticated,)


class FacilityUserViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for FacilityUser add and remove
    """

    queryset = facility_models.FacilityUser.objects.all()
    serializer_class = facility_serializers.FacilityUserSerializer
    permission_classes = (permissions.IsAuthenticated,)
