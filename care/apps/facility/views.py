from rest_framework import viewsets, mixins, permissions

from apps.facility import models as facility_models, serializers as facility_serializers


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
            if self.request.user.user_type.name.lower() == 'facility_user':
                filter_kwargs['facilityuser__user'] = self.request.user
            elif self.request.user.user_type.name.lower() == 'portea':
                filter_kwargs['id__in'] = []
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
