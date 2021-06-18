from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.asset import (
    AssetLocationSerializer,
    AssetSerializer,
    AssetTransactionSerializer,
    UserDefaultAssetLocationSerializer,
)
from care.facility.models.asset import Asset, AssetLocation, AssetTransaction, UserDefaultAssetLocation
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.queryset.asset_location import get_asset_location_queryset
from care.utils.queryset.facility import get_facility_queryset
from rest_framework.serializers import Serializer, UUIDField


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

    @swagger_auto_schema(responses={200: UserDefaultAssetLocationSerializer()})
    @action(detail=False, methods=["GET"])
    def get_default_user_location(self, request, *args, **kwargs):
        obj = get_object_or_404(UserDefaultAssetLocation.objects.filter(user=request.user))
        return Response(UserDefaultAssetLocationSerializer(obj).data)

    class DummyAssetSerializer(Serializer):  # Dummy for Spec
        location = UUIDField(required=True)

    @swagger_auto_schema(request_body=DummyAssetSerializer, responses={200: UserDefaultAssetLocationSerializer()})
    @action(detail=False, methods=["POST"])
    def set_default_user_location(self, request, *args, **kwargs):
        if "location" not in request.data:
            raise ValidationError({"location": "is required"})
        allowed_locations = get_asset_location_queryset(request.user)
        try:
            location = allowed_locations.get(external_id=request.data["location"])
            obj = UserDefaultAssetLocation.objects.filter(user=request.user).first()
            if not obj:
                obj = UserDefaultAssetLocation()
                obj.user = request.user
            obj.location = location
            obj.save()
            return Response(UserDefaultAssetLocationSerializer(obj).data)
        except:
            raise Http404


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

