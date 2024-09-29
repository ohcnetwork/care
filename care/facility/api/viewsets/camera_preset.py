from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.facility.api.serializers.camera_preset import CameraPresetSerializer
from care.facility.models import AssetBed, CameraPreset


class CameraPresetFilter(filters.FilterSet):
    position = filters.BooleanFilter(method="filter_preset_type")
    boundary = filters.BooleanFilter(method="filter_preset_type")

    asset = filters.UUIDFilter(field_name="asset_bed__asset__external_id")
    bed = filters.UUIDFilter(field_name="asset_bed__bed__external_id")
    asset_bed = filters.UUIDFilter(field_name="asset_bed__external_id")

    def filter_preset_type(self, queryset, name, value):
        if value is not None:
            return queryset.filter(**{f"{name}__isnull": not value})
        return queryset


class AssetBedCameraPresetFilter(filters.FilterSet):
    position = filters.BooleanFilter(method="filter_preset_type")
    boundary = filters.BooleanFilter(method="filter_preset_type")

    def filter_preset_type(self, queryset, name, value):
        if value is not None:
            return queryset.filter(**{f"{name}__isnull": not value})
        return queryset


class AssetBedCameraPresetViewSet(ModelViewSet):
    serializer_class = CameraPresetSerializer
    queryset = CameraPreset.objects.all().select_related(
        "asset_bed", "created_by", "updated_by"
    )
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AssetBedCameraPresetFilter

    def get_asset_bed_obj(self):
        return get_object_or_404(
            AssetBed.objects.filter(external_id=self.kwargs["assetbed_external_id"])
        )

    def get_queryset(self):
        asset_bed = self.get_asset_bed_obj()
        return super().get_queryset().filter(asset_bed=asset_bed)

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
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CameraPresetFilter
