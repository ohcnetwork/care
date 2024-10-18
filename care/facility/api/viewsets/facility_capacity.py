from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated

from care.facility.api.serializers.facility_capacity import (
    FacilityCapacityHistorySerializer,
    FacilityCapacitySerializer,
)
from care.facility.api.viewsets import FacilityBaseViewset
from care.facility.models import Facility, FacilityCapacity
from care.users.models import User


class FacilityCapacityViewSet(FacilityBaseViewset, ListModelMixin):
    lookup_field = "external_id"
    serializer_class = FacilityCapacitySerializer
    queryset = FacilityCapacity.objects.filter(facility__deleted=False)
    permission_classes = (IsAuthenticated, DRYPermissions)

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(
            facility__external_id=self.kwargs.get("facility_external_id")
        )
        if user.is_superuser:
            return queryset
        if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return queryset.filter(facility__district=user.district)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(), room_type=self.kwargs.get("external_id")
        )

    def get_facility(self):
        facility_qs = Facility.objects.filter(
            external_id=self.kwargs.get("facility_external_id")
        )
        if not self.request.user.is_superuser:
            facility_qs.filter(users__id__exact=self.request.user.id)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())

    @extend_schema(tags=["capacity"])
    @action(detail=True, methods=["get"])
    def history(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.history.all())
        model = obj.history.__dict__["model"]
        serializer = FacilityCapacityHistorySerializer(model, page, many=True)
        serializer.is_valid()
        return self.get_paginated_response(serializer.data)
