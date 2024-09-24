from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.summary import (
    DistrictSummarySerializer,
    FacilitySummarySerializer,
)
from care.facility.models import DistrictScopedSummary, FacilityRelatedSummary


class FacilitySummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="created_date", lookup_expr="lte")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    district = filters.NumberFilter(field_name="facility__district__id")
    local_body = filters.NumberFilter(field_name="facility__local_body__id")
    state = filters.NumberFilter(field_name="facility__state__id")


class FacilityCapacitySummaryViewSet(
    ListModelMixin,
    GenericViewSet,
):
    lookup_field = "external_id"
    queryset = (
        FacilityRelatedSummary.objects.filter(s_type="FacilityCapacity")
        .order_by("-created_date")
        .select_related(
            "facility",
            "facility__state",
            "facility__district",
            "facility__local_body",
        )
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @extend_schema(tags=["summary"])
    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TriageSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="TriageSummary").order_by(
        "-created_date"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @extend_schema(tags=["summary"])
    @method_decorator(cache_page(60 * 60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TestsSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="TestSummary").order_by(
        "-created_date"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @extend_schema(tags=["summary"])
    @method_decorator(cache_page(60 * 60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PatientSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="PatientSummary").order_by(
        "-created_date"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @extend_schema(tags=["summary"])
    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class DistrictSummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="created_date", lookup_expr="lte")
    district = filters.NumberFilter(field_name="district__id")
    state = filters.NumberFilter(field_name="district__state__id")


class DistrictPatientSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = (
        DistrictScopedSummary.objects.filter(s_type="PatientSummary")
        .order_by("-created_date")
        .select_related("district", "district__state")
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = DistrictSummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DistrictSummaryFilter

    @extend_schema(tags=["summary"])
    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
