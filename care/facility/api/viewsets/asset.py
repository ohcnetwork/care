import re

from django.conf import settings
from django.core.cache import cache
from django.db.models import CharField, Exists, F, OuterRef, Q, Subquery, Value
from django.db.models.fields.json import KT
from django.db.models.functions import Coalesce, NullIf
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES
from djqscsv import render_to_csv_response
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import exceptions
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import UUIDField
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.asset import (
    AssetConfigSerializer,
    AssetLocationSerializer,
    AssetSerializer,
    AssetServiceSerializer,
    AssetTransactionSerializer,
    AvailabilityRecordSerializer,
    DummyAssetOperateResponseSerializer,
    DummyAssetOperateSerializer,
    UserDefaultAssetLocationSerializer,
)
from care.facility.models import (
    Asset,
    AssetLocation,
    AssetService,
    AssetTransaction,
    ConsultationBedAsset,
    UserDefaultAssetLocation,
)
from care.facility.models.asset import (
    AssetTypeChoices,
    AvailabilityRecord,
    StatusChoices,
)
from care.users.models import User
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.assetintegration.base import BaseAssetIntegration
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters.choicefilter import CareChoiceFilter, inverse_choices
from care.utils.queryset.asset_location import get_asset_location_queryset
from care.utils.queryset.facility import get_facility_queryset
from config.authentication import MiddlewareAuthentication

inverse_asset_type = inverse_choices(AssetTypeChoices)
inverse_asset_status = inverse_choices(StatusChoices)


@receiver(post_save, sender=Asset)
def delete_asset_cache(sender, instance, created, **kwargs):
    cache.delete("asset:" + str(instance.external_id))
    cache.delete("asset:qr:" + str(instance.qr_code_id))
    cache.delete("asset:qr:" + str(instance.id))


class AssetLocationViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
    DestroyModelMixin,
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

    def get_serializer_context(self):
        facility = self.get_facility()
        context = super().get_serializer_context()
        context["facility"] = facility
        return context

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.bed_set.filter(deleted=False).count():
            raise ValidationError("Cannot delete a Location with associated Beds")
        if instance.asset_set.filter(deleted=False).count():
            raise ValidationError("Cannot delete a Location with associated Assets")

        return super().destroy(request, *args, **kwargs)


class AssetFilter(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="current_location__facility__external_id")
    location = filters.UUIDFilter(field_name="current_location__external_id")
    asset_type = CareChoiceFilter(choice_dict=inverse_asset_type)
    asset_class = filters.CharFilter(field_name="asset_class")
    status = CareChoiceFilter(choice_dict=inverse_asset_status)
    is_working = filters.BooleanFilter()
    qr_code_id = filters.CharFilter(field_name="qr_code_id", lookup_expr="icontains")
    in_use_by_consultation = filters.BooleanFilter(
        method="filter_in_use_by_consultation"
    )
    is_permanent = filters.BooleanFilter(method="filter_is_permanent")
    warranty_amc_end_of_validity = filters.DateFromToRangeFilter()

    def filter_in_use_by_consultation(self, queryset, _, value):
        if value not in EMPTY_VALUES:
            queryset = queryset.annotate(
                is_in_use=Exists(
                    ConsultationBedAsset.objects.filter(
                        Q(consultation_bed__end_date__gt=timezone.now())
                        | Q(consultation_bed__end_date__isnull=True),
                        asset=OuterRef("pk"),
                    )
                )
            )
            queryset = queryset.filter(is_in_use=value)
        return queryset.distinct()

    def filter_is_permanent(self, queryset, _, value):
        if value not in EMPTY_VALUES:
            if value:
                queryset = queryset.filter(
                    asset_class__in=[
                        AssetClasses.ONVIF.name,
                        AssetClasses.HL7MONITOR.name,
                    ]
                )
            else:
                queryset = queryset.exclude(
                    asset_class__in=[
                        AssetClasses.ONVIF.name,
                        AssetClasses.HL7MONITOR.name,
                    ]
                )
        return queryset.distinct()


class AssetPublicViewSet(GenericViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    lookup_field = "external_id"

    def retrieve(self, request, *args, **kwargs):
        key = "asset:" + kwargs["external_id"]
        hit = cache.get(key)
        if not hit:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            cache.set(
                key, serializer.data, 60 * 60 * 24
            )  # Cache the asset details for 24 hours
            return Response(serializer.data)
        return Response(hit)


class AssetPublicQRViewSet(GenericViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    lookup_field = "qr_code_id"

    def retrieve(self, request, *args, **kwargs):
        qr_code_id = kwargs["qr_code_id"]
        key = "asset:qr:" + qr_code_id
        hit = cache.get(key)
        if not hit:
            instance = self.get_queryset().filter(qr_code_id=qr_code_id).first()
            if not instance:  # If the asset is not found, try to find it by pk
                if not qr_code_id.isnumeric():
                    return Response(status=status.HTTP_404_NOT_FOUND)
                instance = get_object_or_404(self.get_queryset(), pk=qr_code_id)
            serializer = self.get_serializer(instance)
            cache.set(key, serializer.data, 60 * 60 * 24)
            return Response(serializer.data)
        return Response(hit)


class AvailabilityViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = AvailabilityRecord.objects.all()
    serializer_class = AvailabilityRecordSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        facility_queryset = get_facility_queryset(self.request.user)
        if "asset_external_id" in self.kwargs:
            asset = get_object_or_404(
                Asset, external_id=self.kwargs["asset_external_id"]
            )
            if asset.current_location.facility in facility_queryset:
                return self.queryset.filter(
                    content_type__model="asset",
                    object_external_id=self.kwargs["asset_external_id"],
                )
            else:
                raise exceptions.PermissionDenied(
                    "You do not have access to this asset's availability records"
                )
        elif "asset_location_external_id" in self.kwargs:
            asset_location = get_object_or_404(
                AssetLocation, external_id=self.kwargs["asset_location_external_id"]
            )
            if asset_location.facility in facility_queryset:
                return self.queryset.filter(
                    content_type__model="assetlocation",
                    object_external_id=self.kwargs["asset_location_external_id"],
                )
            else:
                raise exceptions.PermissionDenied(
                    "You do not have access to this asset location's availability records"
                )
        else:
            raise exceptions.ValidationError(
                "Either asset_external_id or asset_location_external_id is required"
            )


class AssetViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
    DestroyModelMixin,
):
    queryset = (
        Asset.objects.all()
        .select_related("current_location", "current_location__facility")
        .order_by("-created_date")
    )
    serializer_class = AssetSerializer
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ["name", "serial_number", "qr_code_id"]
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
        queryset = queryset.annotate(
            latest_status=Subquery(
                AvailabilityRecord.objects.filter(
                    content_type__model="asset",
                    object_external_id=OuterRef("external_id"),
                )
                .order_by("-created_date")
                .values("status")[:1]
            )
        )
        return queryset

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            mapping = Asset.CSV_MAPPING.copy()
            queryset = self.filter_queryset(self.get_queryset()).values(*mapping.keys())
            pretty_mapping = Asset.CSV_MAKE_PRETTY.copy()
            return render_to_csv_response(
                queryset, field_header_map=mapping, field_serializer_map=pretty_mapping
            )

        return super(AssetViewSet, self).list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.request.user
        if user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return super().destroy(request, *args, **kwargs)
        else:
            raise exceptions.AuthenticationFailed(
                "Only District Admin and above can delete assets"
            )

    @extend_schema(
        responses={200: UserDefaultAssetLocationSerializer()}, tags=["asset"]
    )
    @action(detail=False, methods=["GET"])
    def get_default_user_location(self, request, *args, **kwargs):
        obj = get_object_or_404(
            UserDefaultAssetLocation.objects.filter(user=request.user)
        )
        return Response(UserDefaultAssetLocationSerializer(obj).data)

    @extend_schema(
        request=inline_serializer(
            "AssetLocationFieldSerializer", fields={"location": UUIDField()}
        ),
        responses={200: UserDefaultAssetLocationSerializer()},
        tags=["asset"],
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
        except Exception as e:
            raise Http404 from e

    @extend_schema(
        request=DummyAssetOperateSerializer,
        responses={200: DummyAssetOperateResponseSerializer},
        tags=["asset"],
    )
    @action(detail=True, methods=["POST"])
    def operate_assets(self, request, *args, **kwargs):
        """
        This API is used to operate assets. API accepts the asset_id and action as parameters.
        """
        try:
            action = request.data["action"]
            asset: Asset = self.get_object()
            middleware_hostname = (
                asset.meta.get(
                    "middleware_hostname",
                )
                or asset.current_location.middleware_address
                or asset.current_location.facility.middleware_address
            )
            asset_class: BaseAssetIntegration = AssetClasses[asset.asset_class].value(
                {
                    **asset.meta,
                    "middleware_hostname": middleware_hostname,
                }
            )
            result = asset_class.handle_action(action)
            return Response({"result": result}, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({"detail": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as e:
            return Response(
                {"message": {key: "is required" for key in e.args}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except APIException as e:
            return Response(
                {
                    "detail": f"Communication with the middleware failed.\nReceived status code: {e.status_code}"
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception as e:
            print(f"error: {e}")
            return Response(
                {"message": "Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AssetRetrieveConfigViewSet(ListModelMixin, GenericViewSet):
    queryset = Asset.objects.all()
    authentication_classes = [MiddlewareAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = AssetConfigSerializer

    @extend_schema(
        tags=["asset"],
        parameters=[
            OpenApiParameter(
                name="middleware_hostname",
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        """
        This API is used by the middleware to retrieve assets and their configurations
        for a given facility and middleware hostname.
        """
        middleware_hostname = request.query_params.get("middleware_hostname")
        if not middleware_hostname:
            return Response(
                {"middleware_hostname": "Middleware hostname is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if match := re.match(r"^(https?://)?([^\s/]+)/?$", middleware_hostname):
            middleware_hostname = match.group(2)  # extract the hostname from the URL
        else:
            return Response(
                {"middleware_hostname": "Invalid middleware hostname"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            self.get_queryset()
            .filter(
                current_location__facility=self.request.user.facility,
                asset_class__in=[
                    AssetClasses.ONVIF.name,
                    AssetClasses.HL7MONITOR.name,
                ],
            )
            .annotate(
                resolved_middleware_hostname=Coalesce(
                    NullIf(KT("meta__middleware_hostname"), Value("")),
                    NullIf(F("current_location__middleware_address"), Value("")),
                    F("current_location__facility__middleware_address"),
                    output_field=CharField(),
                )
            )
            .filter(resolved_middleware_hostname=middleware_hostname)
            .exclude(
                Q(meta__local_ip_address__isnull=True)
                | Q(meta__local_ip_address__exact=""),
            )
        ).only("external_id", "meta", "description", "name", "asset_class")

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AssetTransactionFilter(filters.FilterSet):
    qr_code_id = filters.CharFilter(field_name="asset__qr_code_id")
    external_id = filters.CharFilter(field_name="asset__external_id")


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


class AssetServiceFilter(filters.FilterSet):
    qr_code_id = filters.CharFilter(field_name="asset__qr_code_id")
    external_id = filters.CharFilter(field_name="asset__external_id")


class AssetServiceViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = (
        AssetService.objects.all()
        .select_related(
            "asset",
        )
        .prefetch_related("edits")
        .order_by("-created_date")
    )
    serializer_class = AssetServiceSerializer

    permission_classes = (IsAuthenticated,)

    lookup_field = "external_id"

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AssetServiceFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(
            asset__external_id=self.kwargs.get("asset_external_id")
        )
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(
                asset__current_location__facility__state=user.state
            )
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                asset__current_location__facility__district=user.district
            )
        else:
            allowed_facilities = get_accessible_facilities(user)
            queryset = queryset.filter(
                asset__current_location__facility__id__in=allowed_facilities
            )
        return queryset
