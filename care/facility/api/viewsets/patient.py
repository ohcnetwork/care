import json
from json import JSONDecodeError

from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from care.facility.api.mixins import HistoryMixin
from care.facility.api.serializers.patient import (
    FacilityPatientStatsHistorySerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientSearchSerializer,
)
from care.facility.models import Facility, FacilityPatientStatsHistory, PatientRegistration, PatientSearch
from care.facility.models.patient_base import DiseaseStatusEnum
from care.users.models import User


class PatientFilterSet(filters.FilterSet):
    facility = filters.NumberFilter(field_name="facility_id")
    phone_number = filters.CharFilter(field_name="phone_number")


class PatientDRYFilter(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if view.action == "list":
            queryset = self.filter_list_queryset(request, queryset, view)

        if not request.user.is_superuser:
            if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                queryset = queryset.filter(state=request.user.state)
            elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
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
        "local_body", "district", "state", "facility", "facility__local_body", "facility__district", "facility__state"
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
            disease_status = filter_query if filter_query.isdigit() else DiseaseStatusEnum[filter_query].value
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

    @action(detail=False)
    def search(self, request, *args, **kwargs):
        serializer = PatientSearchSerializer(data=request.query_params, partial=True)
        serializer.is_valid(raise_exception=True)

        search_keys = ["date_of_birth", "year_of_birth", "phone_number"]
        search_fields = {
            key: serializer.validated_data[key] for key in search_keys if serializer.validated_data.get(key)
        }
        if not search_fields:
            raise serializers.ValidationError(
                {"detail": [f"None of the search keys provided. Available: {', '.join(search_keys)}"]}
            )

        if not request.user.is_superuser:
            search_fields["state_id"] = request.user.state_id
        result_qs = PatientSearch.objects.filter(**search_fields)
        page = self.paginate_queryset(result_qs)
        result_serializer = PatientSearchSerializer(page, many=True)
        return self.get_paginated_response(result_serializer.data)


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
