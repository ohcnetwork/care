from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.facility.api.serializers.camera_preset import CameraPresetSerializer
from care.facility.models import Asset, AssetBed, Bed, CameraPreset
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities


class AssetBedCameraPresetViewSet(ModelViewSet):
    serializer_class = CameraPresetSerializer
    queryset = CameraPreset.objects.all().select_related(
        "asset_bed", "created_by", "updated_by"
    )
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)

    def get_asset_bed_obj(self):
        user = self.request.user
        queryset = AssetBed.objects.filter(
            external_id=self.kwargs["assetbed_external_id"]
        )
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(bed__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(bed__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(bed__facility__id__in=allowed_facilities)
        return get_object_or_404(queryset)

    def get_queryset(self):
        return super().get_queryset().filter(asset_bed=self.get_asset_bed_obj())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["asset_bed"] = self.get_asset_bed_obj()
        return context


class CameraPresetViewSet(GenericViewSet, ListModelMixin):
    serializer_class = CameraPresetSerializer
    queryset = CameraPreset.objects.all().select_related(
        "asset_bed", "created_by", "updated_by"
    )
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)

    def get_bed_obj(self, external_id: str):
        user = self.request.user
        queryset = Bed.objects.filter(external_id=external_id)
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(facility__id__in=allowed_facilities)
        return get_object_or_404(queryset)

    def get_asset_obj(self, external_id: str):
        user = self.request.user
        queryset = Asset.objects.filter(external_id=external_id)
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(current_location__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                current_location__facility__district=user.district
            )
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(
                current_location__facility__id__in=allowed_facilities
            )
        return get_object_or_404(queryset)

    def get_queryset(self):
        queryset = super().get_queryset()
        if asset_external_id := self.kwargs.get("asset_external_id"):
            return queryset.filter(
                asset_bed__asset=self.get_asset_obj(asset_external_id)
            )
        if bed_external_id := self.kwargs.get("bed_external_id"):
            return queryset.filter(asset_bed__bed=self.get_bed_obj(bed_external_id))
        raise NotFound
