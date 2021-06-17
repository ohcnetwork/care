from django.shortcuts import get_object_or_404
from care.utils.queryset.facility import get_facility_queryset
from care.facility.models.asset import AssetLocation
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin

from care.facility.api.serializers.asset import AssetLocationSerializer
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class AssetLocationViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = AssetLocation.objects.all()
    serializer_class = AssetLocationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(facility__id__in=allowed_facilities)
        return super().get_queryset()

    def get_facility(self):
        facilities = get_facility_queryset(self.request.user)
        return get_object_or_404(facilities.filter(external_id=self.kwargs["facility_external_id"]))

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())
