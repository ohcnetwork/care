from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import CharField, JSONField, Serializer, UUIDField
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.asset import (
    AssetLocationSerializer,
    AssetSerializer,
    AssetTransactionSerializer,
    UserDefaultAssetLocationSerializer,
)
from care.facility.models.asset import (
    Asset,
    AssetLocation,
    AssetTransaction,
    UserDefaultAssetLocation,
)
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.assetintegration.base import BaseAssetIntegration
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters.choicefilter import CareChoiceFilter, inverse_choices
from care.utils.queryset.asset_location import get_asset_location_queryset
from care.utils.queryset.facility import get_facility_queryset

inverse_asset_type = inverse_choices(Asset.AssetTypeChoices)
inverse_asset_status = inverse_choices(Asset.StatusChoices)


class AssetLocationViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = (
        AssetLocation.objects.all().select_related("facility").order_by("-created_date")
    )
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    serializer_class = AssetLocationSerializer
    lookup_field = "external_id"
    filter_backends = (drf_filters.SearchFilter,)
    search_fields = ["name"]

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

        return queryset.filter(
            facility__external_id=self.kwargs["facility_external_id"]
        )

    def get_facility(self):
        facilities = get_facility_queryset(self.request.user)
        return get_object_or_404(
            facilities.filter(external_id=self.kwargs["facility_external_id"])
        )

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())


class AssetFilter(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="current_location__facility__external_id")
    location = filters.UUIDFilter(field_name="current_location__external_id")
    asset_type = CareChoiceFilter(choice_dict=inverse_asset_type)
    status = CareChoiceFilter(choice_dict=inverse_asset_status)
    is_working = filters.BooleanFilter() 
    qr_code_id = filters.CharFilter(field_name="qr_code_id", lookup_expr="icontains")


class AssetViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = (
        Asset.objects.all()
        .select_related("current_location", "current_location__facility")
        .order_by("-created_date")
    )
    serializer_class = AssetSerializer
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ["name"]
    permission_classes = [IsAuthenticated]
    filterset_class = AssetFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
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
        return queryset

    @swagger_auto_schema(responses={200: UserDefaultAssetLocationSerializer()})
    @action(detail=False, methods=["GET"])
    def get_default_user_location(self, request, *args, **kwargs):
        obj = get_object_or_404(
            UserDefaultAssetLocation.objects.filter(user=request.user)
        )
        return Response(UserDefaultAssetLocationSerializer(obj).data)

    class DummyAssetSerializer(Serializer):  # Dummy for Spec
        location = UUIDField(required=True)

    @swagger_auto_schema(
        request_body=DummyAssetSerializer,
        responses={200: UserDefaultAssetLocationSerializer()},
    )
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

    # Dummy Serializer for Operate Asset
    class DummyAssetOperateSerializer(Serializer):
        action = JSONField(required=True)

    class DummyAssetOperateResponseSerializer(Serializer):
        message = CharField(required=True)
        result = JSONField(required=False)

    # Asset Integration API
    @swagger_auto_schema(
        request_body=DummyAssetOperateSerializer,
        responses={200: DummyAssetOperateResponseSerializer},
    )
    @action(detail=True, methods=["POST"])
    def operate_assets(self, request, *args, **kwargs):
        """
        This API is used to operate assets. API accepts the asset_id and action as parameters.
        """
        try:
            action = request.data["action"]
            asset: Asset = self.get_object()
            asset_class: BaseAssetIntegration = AssetClasses[asset.asset_class].value(
                asset.meta)
            result = asset_class.handle_action(action)
            return Response({"result": result}, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({"message": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as e:
            return Response({
                "message": dict((key, "is required") for key in e.args)
            }, status=status.HTTP_400_BAD_REQUEST)

        except APIException as e:
            return Response(e.detail, e.status_code)

        except Exception as e:
            print(f"error: {e}")
            return Response(
                {"message": "Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AssetTransactionFilter(filters.FilterSet):
    asset = filters.UUIDFilter(field_name="asset__external_id")


class AssetTransactionViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = (
        AssetTransaction.objects.all()
        .select_related(
            "from_location",
            "to_location",
            "from_location__facility",
            "to_location__facility",
            "performed_by",
            "asset",
        )
        .order_by("-created_date")
    )
    serializer_class = AssetTransactionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AssetTransactionFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(
                Q(from_location__facility__state=user.state)
                | Q(to_location__facility__state=user.state)
            )
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                Q(from_location__facility__district=user.district)
                | Q(to_location__facility__district=user.district)
            )
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(
                Q(from_location__facility__id__in=allowed_facilities)
                | Q(to_location__facility__id__in=allowed_facilities)
            )
        return queryset
