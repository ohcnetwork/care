from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.asset import AssetLocationSerializer, AssetSerializer, AssetTransactionSerializer
from care.facility.models.asset import Asset, AssetLocation, AssetTransaction
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.queryset.facility import get_facility_queryset


class AssetLocationViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = AssetLocation.objects.all().select_related("facility")
    serializer_class = AssetLocationSerializer
    lookup_field = "external_id"

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


class AssetViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Asset.objects.all().select_related("current_location", "current_location__facility")
    serializer_class = AssetSerializer
    lookup_field = "external_id"

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(current_location__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(current_location__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(current_location__facility__id__in=allowed_facilities)
        return super().get_queryset()


class AssetTransactionViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = AssetTransaction.objects.all().select_related(
        "from_location", "to_location", "from_location__facility", "to_location__facility", "performed_by", "asset"
    )
    serializer_class = AssetTransactionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(
                Q(from_location__facility__state=user.state) | Q(to_location__facility__state=user.state)
            )
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                Q(from_location__facility__district=user.district) | Q(to_location__facility__district=user.district)
            )
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(
                Q(from_location__facility__id__in=allowed_facilities)
                | Q(to_location__facility__id__in=allowed_facilities)
            )
        return super().get_queryset()

