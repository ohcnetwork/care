import json
from json import JSONDecodeError

from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import HistoryMixin
from care.facility.api.serializers.patient import (
    FacilityPatientStatsHistorySerializer,
    PatientDetailSerializer,
    PatientListSerializer,
)
from care.facility.models import DISEASE_CHOICES_VALUES, Facility, FacilityPatientStatsHistory, PatientRegistration
from care.users.models import User


class PatientFilterSet(filters.FilterSet):
    facility = filters.NumberFilter(field_name="facility_id")
    phone_number = filters.CharFilter(field_name="phone_number")


class PatientDRYFilter(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if view.action == "list":
            queryset = self.filter_list_queryset(request, queryset, view)

        if not request.user.is_superuser:
            if request.user.user_type >= User.TYPE_VALUES.choices.StateLabAdmin.value:
                queryset = queryset.filter(state=request.user.state)
            elif request.user.user_type >= User.TYPE_VALUES.choices.DistrictLabAdmin.value:
                queryset = queryset.filter(district=request.user.district)
            else:
                queryset = queryset.filter(Q(created_by=request.user) | Q(facility__created_by=request.user))
        return queryset

    def filter_list_queryset(self, request, queryset, view):
        try:
            show_without_facility = json.loads(request.query_params.get("without_facility"))
        except (
            JSONDecodeError,
            TypeError,
        ):
            show_without_facility = False
        return queryset.filter(facility_id__isnull=show_without_facility)


class PatientViewSet(HistoryMixin, viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = PatientRegistration.objects.all().select_related(
        "local_body", "district", "state", "facility", "facility__local_body", "facility__district", "facility__state",
    )
    serializer_class = PatientDetailSerializer
    filter_backends = (
        PatientDRYFilter,
        filters.DjangoFilterBackend,
    )
    filterset_class = PatientFilterSet

    def get_queryset(self):
        filter_query = self.request.query_params.get("disease_status")
        queryset = super().get_queryset()
        if filter_query:
            disease_status = filter_query if filter_query.isdigit() else DISEASE_CHOICES_VALUES[filter_query].value
            return queryset.filter(disease_status=disease_status)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        else:
            return self.serializer_class

    def list(self, request, *args, **kwargs):
        """
        Patient List

        `without_facility` accepts boolean - default is false -
            if true: shows only patients without a facility mapped
            if false (default behaviour): shows only patients with a facility mapped

        `disease_status` accepts - string and int -
            SUSPECTED = 1
            POSITIVE = 2
            NEGATIVE = 3
            RECOVERY = 4
            RECOVERED = 5
            EXPIRED = 6

        """
        return super(PatientViewSet, self).list(request, *args, **kwargs)


class FacilityPatientStatsHistoryFilterSet(filters.FilterSet):
    entry_date = filters.DateFromToRangeFilter(field_name="entry_date")


class FacilityPatientStatsHistoryViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = FacilityPatientStatsHistory.objects.all().order_by("-entry_date")
    serializer_class = FacilityPatientStatsHistorySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityPatientStatsHistoryFilterSet
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(facility_id=self.kwargs.get("facility_pk"))

    def get_object(self):
        return get_object_or_404(self.get_queryset(), id=self.kwargs.get("pk"))

    def get_facility(self):
        facility_qs = Facility.objects.filter(pk=self.kwargs.get("facility_pk"))
        if not self.request.user.is_superuser:
            facility_qs.filter(created_by=self.request.user)
        return get_object_or_404(facility_qs)

    def perform_create(self, serializer):
        return serializer.save(facility=self.get_facility())

    def list(self, request, *args, **kwargs):
        """
        Patient Stats - List

        Available Filters
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date

        """
        return super(FacilityPatientStatsHistoryViewSet, self).list(request, *args, **kwargs)
