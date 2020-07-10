import datetime
import json
from json import JSONDecodeError
from config.celery_app import app
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.validators import validate_email
from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient import (
    FacilityPatientStatsHistorySerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientSearchSerializer,
    PatientTransferSerializer,
)
from care.facility.api.serializers.patient_icmr import PatientICMRSerializer
from care.facility.api.viewsets import UserAccessMixin
from care.facility.api.viewsets.mixins.history import HistoryMixin
from care.facility.models import Facility, FacilityPatientStatsHistory, PatientRegistration, PatientSearch
from care.facility.models.patient_base import DiseaseStatusEnum
from care.facility.models.patient_icmr import PatientIcmr
from care.users.models import User

from care.facility.tasks.patient.discharge_report import generate_discharge_report

from config.celery_app import app


class PatientFilterSet(filters.FilterSet):
    source = filters.ChoiceFilter(choices=PatientRegistration.SourceChoices)
    facility = filters.UUIDFilter(field_name="facility__external_id")
    phone_number = filters.CharFilter(field_name="phone_number")


class PatientDRYFilter(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if view.action == "list":
            queryset = self.filter_list_queryset(request, queryset, view)

        if not request.user.is_superuser:
            if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                queryset = queryset.filter(facility__state=request.user.state)
            elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                queryset = queryset.filter(facility__district=request.user.district)
            elif view.action != "transfer":
                queryset = queryset.filter(
                    Q(created_by=request.user) | Q(facility__users__id__exact=request.user.id)
                ).distinct("id")
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
    lookup_field = "external_id"
    queryset = PatientRegistration.objects.all().select_related(
        "local_body",
        "district",
        "state",
        "facility",
        "facility__local_body",
        "facility__district",
        "facility__state",
        "nearest_facility",
        "nearest_facility__local_body",
        "nearest_facility__district",
        "nearest_facility__state",
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
        elif self.action == "icmr_sample":
            return PatientICMRSerializer
        elif self.action == "transfer":
            return PatientTransferSerializer
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
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            queryset = self.filter_queryset(self.get_queryset()).values(*PatientRegistration.CSV_MAPPING.keys())
            return render_to_csv_response(
                queryset,
                field_header_map=PatientRegistration.CSV_MAPPING,
                field_serializer_map=PatientRegistration.CSV_MAKE_PRETTY,
            )
        return super(PatientViewSet, self).list(request, *args, **kwargs)

    @action(detail=True, methods=["POST"])
    def discharge_patient(self, request, *args, **kwargs):
        discharged = bool(request.data.get("discharge", False))
        patient = self.get_object()
        patient.is_active = discharged
        patient.allow_transfer = not discharged
        patient.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def discharge_summary(self, request, *args, **kwargs):
        patient = self.get_object()
        email = request.data.get("email", "")
        try:
            validate_email(email)
        except:
            email = request.user.email
        generate_discharge_report.delay(patient.id, email)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        patient = PatientRegistration.objects.get(
            id=PatientSearch.objects.get(external_id=kwargs["external_id"]).patient_id
        )

        if patient.allow_transfer == False:
            return Response(
                {"Patient": "Cannot Transfer Patient , Source Facility Does Not Allow"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        serializer = self.get_serializer_class()(patient, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        patient = PatientRegistration.objects.get(
            id=PatientSearch.objects.get(external_id=kwargs["external_id"]).patient_id
        )
        response_serializer = self.get_serializer_class()(patient)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)


class FacilityPatientStatsHistoryFilterSet(filters.FilterSet):
    entry_date = filters.DateFromToRangeFilter(field_name="entry_date")


class FacilityPatientStatsHistoryViewSet(viewsets.ModelViewSet):
    lookup_field = "external_id"
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = FacilityPatientStatsHistory.objects.all().order_by("-entry_date")
    serializer_class = FacilityPatientStatsHistorySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityPatientStatsHistoryFilterSet
    http_method_names = ["get", "post", "delete"]

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
        return serializer.save(facility=self.get_facility())

    def list(self, request, *args, **kwargs):
        """
        Patient Stats - List

        Available Filters
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date

        """
        return super(FacilityPatientStatsHistoryViewSet, self).list(request, *args, **kwargs)


class PatientSearchViewSet(UserAccessMixin, ListModelMixin, GenericViewSet):
    http_method_names = ["get"]
    queryset = PatientSearch.objects.all()
    serializer_class = PatientSearchSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)

    def get_queryset(self):
        if self.action != "list":
            return super(PatientSearchViewSet, self).get_queryset()
        else:
            serializer = PatientSearchSerializer(data=self.request.query_params, partial=True)
            serializer.is_valid(raise_exception=True)
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                search_keys = ["date_of_birth", "year_of_birth", "phone_number", "name", "age"]
            else:
                search_keys = ["date_of_birth", "year_of_birth", "phone_number", "age"]
            search_fields = {
                key: serializer.validated_data[key] for key in search_keys if serializer.validated_data.get(key)
            }
            if not search_fields:
                raise serializers.ValidationError(
                    {"detail": [f"None of the search keys provided. Available: {', '.join(search_keys)}"]}
                )

            if not self.request.user.is_superuser:
                search_fields["state_id"] = self.request.user.state_id

            if "age" in search_fields:
                age = search_fields.pop("age")
                year_of_birth = datetime.datetime.now().year - age
                search_fields["age__gte"] = year_of_birth - 5
                search_fields["age__lte"] = year_of_birth + 5

            name = search_fields.pop("name", None)

            queryset = self.queryset.filter(**search_fields)

            if name:
                queryset = (
                    queryset.annotate(similarity=TrigramSimilarity("name", name))
                    .filter(similarity__gt=0.2)
                    .order_by("-similarity")
                )

            return queryset

    def retrieve(self, request, *args, **kwargs):
        raise NotImplementedError()

    def list(self, request, *args, **kwargs):
        """
        Patient Search

        ### Available filters -

        - year_of_birth: in YYYY format
        - date_of_birth: in YYYY-MM-DD format
        - phone_number: in E164 format: eg: +917795937091
        - name: free text search
        - age: number - searches age +/- 5 years

        **SPECIAL NOTE**: the values should be urlencoded

        `Eg: api/v1/patient/search/?year_of_birth=1992&phone_number=%2B917795937091`

        """
        return super(PatientSearchViewSet, self).list(request, *args, **kwargs)
