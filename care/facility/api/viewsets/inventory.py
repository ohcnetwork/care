from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.inventory import (
    FacilityInventoryBurnRateSerializer,
    FacilityInventoryItemSerializer,
    FacilityInventoryLogSerializer,
    FacilityInventoryMinQuantitySerializer,
    FacilityInventorySummarySerializer,
)
from care.facility.api.viewsets.mixins.access import UserAccessMixin
from care.facility.models import (
    Facility,
    FacilityInventoryBurnRate,
    FacilityInventoryItem,
    FacilityInventoryLog,
    FacilityInventoryMinQuantity,
    FacilityInventorySummary,
)
from care.users.models import User


class FacilityInventoryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class FacilityInventoryItemViewSet(
    UserAccessMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet,
):
    serializer_class = FacilityInventoryItemSerializer
    queryset = (
        FacilityInventoryItem.objects.select_related("default_unit").prefetch_related("allowed_units", "tags").all()
    )
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityInventoryFilter

    def list(self, request, *args, **kwargs):
        """
        Facility Capacity List

        /facility/{facility_pk}/capacity/{pk}
        `pk` in the API refers to the room_type.
        """
        return super(FacilityInventoryItemViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Facility Capacity Retrieve

        /facility/{facility_pk}/capacity/{pk}
        `pk` in the API refers to the room_type.
        """
        return super(FacilityInventoryItemViewSet, self).retrieve(request, *args, **kwargs)


class FacilityInventoryLogFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    item = filters.NumberFilter(field_name="item__id")


class FacilityInventoryLogViewSet(
    UserAccessMixin, RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet,
):
    lookup_field = "external_id"
    serializer_class = FacilityInventoryLogSerializer
    queryset = FacilityInventoryLog.objects.select_related("item", "unit").order_by("-created_date")
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityInventoryLogFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), external_id=self.kwargs.get("external_id"))

    def get_facility(self):
        facility_qs = Facility.objects.filter(external_id=self.kwargs.get("facility_external_id"))
        if not self.request.user.is_superuser:
            facility_qs.filter(users__id__exact=self.request.user.id)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())


class FacilityInventoryMinQuantityViewSet(
    UserAccessMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, ListModelMixin, GenericViewSet,
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
        queryset = self.queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), external_id=self.kwargs.get("external_id"))

    def get_facility(self):
        facility_qs = Facility.objects.filter(external_id=self.kwargs.get("facility_external_id"))
        if not self.request.user.is_superuser:
            facility_qs.filter(users__id__exact=self.request.user.id)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        serializer.save(facility=self.get_facility())


class FacilityInventorySummaryViewSet(
    UserAccessMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet,
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
        queryset = self.queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), external_id=self.kwargs.get("external_id"))


class FacilityInventoryBurnRateFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="facility__name", lookup_expr="icontains")
    item = filters.NumberFilter(field_name="item_id")


class FacilityInventoryBurnRateViewSet(
    UserAccessMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet,
):
    queryset = FacilityInventoryBurnRate.objects.select_related(
        "item", "item__default_unit", "facility__district"
    ).all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityInventoryBurnRateFilter
    permission_classes = (IsAuthenticated, DRYPermissions)
    serializer_class = FacilityInventoryBurnRateSerializer

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.kwargs.get("facility_external_id"):
            queryset = queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        return self.filter_by_user_scope(queryset)
