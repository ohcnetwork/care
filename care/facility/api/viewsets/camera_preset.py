from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from care.facility.api.serializers.camera_preset import CameraPresetSerializer
from care.facility.models import AssetBed, CameraPreset


class CameraPresetFilter(filters.FilterSet):
    position = filters.ChoiceFilter(method="filter_preset_type")
    boundary = filters.BooleanFilter(method="filter_preset_type")

    def filter_preset_type(self, queryset, name, value):
        if value is not None:
            return queryset.filter(**{f"${name}__is_null": not value})


class CameraPresetViewSet(ModelViewSet):
    serializer_class = CameraPresetSerializer
    queryset = CameraPreset.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated, DRYPermissions)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CameraPresetFilter

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
