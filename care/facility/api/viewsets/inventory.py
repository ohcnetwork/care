from django.db import transaction
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.inventory import (
    FacilityInventoryItemSerializer,
    FacilityInventoryLogSerializer,
    FacilityInventoryMinQuantitySerializer,
    FacilityInventorySummarySerializer,
    set_burn_rate,
)
from care.facility.api.viewsets.mixins.access import UserAccessMixin
from care.facility.models import (
    Facility,
    FacilityInventoryItem,
    FacilityInventoryLog,
    FacilityInventoryMinQuantity,
    FacilityInventorySummary,
)
from care.users.models import User
from care.utils.queryset.facility import get_facility_queryset


def check_integer(vals):
    if not isinstance(vals, list):
        vals = [vals]
    for i in range(len(vals)):
        try:
            vals[i] = int(vals[i])
        except Exception as e:
            raise ValidationError({"value": "Integer Required"}) from e
    return vals


class FacilityInventoryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class FacilityInventoryItemViewSet(
    UserAccessMixin,
    RetrieveModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    serializer_class = FacilityInventoryItemSerializer
    queryset = (
        FacilityInventoryItem.objects.select_related("default_unit")
        .prefetch_related("allowed_units", "tags")
        .all()
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityInventoryFilter


class FacilityInventoryLogFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    item = filters.NumberFilter(field_name="item__id")


class FacilityInventoryLogViewSet(
    UserAccessMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = FacilityInventoryLogSerializer
    queryset = FacilityInventoryLog.objects.select_related("item", "unit").order_by(
        "-created_date"
    )
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityInventoryLogFilter

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
            self.get_queryset(), external_id=self.kwargs.get("external_id")
        )

    def get_facility(self):
        queryset = get_facility_queryset(self.request.user)
        return get_object_or_404(
            queryset.filter(external_id=self.kwargs.get("facility_external_id"))
        )

    @extend_schema(tags=["inventory"])
    @action(methods=["PUT"], detail=True)
    def flag(self, request, **kwargs):
        log_obj = get_object_or_404(
            self.get_queryset(), external_id=self.kwargs.get("external_id")
        )
        log_obj.probable_accident = not log_obj.probable_accident
        log_obj.save()
        set_burn_rate(log_obj.facility, log_obj.item)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["inventory"])
    @action(methods=["DELETE"], detail=False)
    def delete_last(self, request, **kwargs):
        facility = self.get_facility()
        item = self.request.GET.get("item")
        if not item:
            raise ValidationError({"item": "is required"})
        item = check_integer(item)[0]
        item_obj = get_object_or_404(FacilityInventoryItem.objects.filter(id=item))
        inventory_log_object = FacilityInventoryLog.objects.filter(
            item=item_obj, facility=facility
        ).order_by("-id")
        if not inventory_log_object.exists():
            raise ValidationError({"inventory": "Does not Exist"})
        inventory_log_object = inventory_log_object[0]
        data = self.get_serializer(inventory_log_object).data
        with transaction.atomic():
            data["is_incoming"] = not data["is_incoming"]
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save(facility=facility, probable_accident=True)
            inventory_log_object.probable_accident = True
            inventory_log_object.save()
            serializer.set_burn_rate(facility, item_obj)
        return Response(status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())


class FacilityInventoryMinQuantityViewSet(
    UserAccessMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = FacilityInventoryMinQuantitySerializer
    queryset = FacilityInventoryMinQuantity.objects.filter(deleted=False)
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )

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
            self.get_queryset(), external_id=self.kwargs.get("external_id")
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


class FacilityInventorySummaryViewSet(
    UserAccessMixin,
    RetrieveModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = FacilityInventorySummarySerializer
    queryset = FacilityInventorySummary.objects.filter(deleted=False)
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )

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
            self.get_queryset(), external_id=self.kwargs.get("external_id")
        )
