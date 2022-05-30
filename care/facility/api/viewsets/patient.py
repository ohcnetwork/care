import datetime
import json
from json import JSONDecodeError

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.validators import validate_email
from django.db.models.query_utils import Q
from django.utils.timezone import localtime, now
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient import (
    FacilityPatientStatsHistorySerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientNotesSerializer,
    PatientSearchSerializer,
    PatientTransferSerializer,
)
from care.facility.api.serializers.patient_icmr import PatientICMRSerializer
from care.facility.api.viewsets import UserAccessMixin
from care.facility.api.viewsets.mixins.history import HistoryMixin
from care.facility.models import (
    CATEGORY_CHOICES,
    FACILITY_TYPES,
    Facility,
    FacilityPatientStatsHistory,
    PatientConsultation,
    PatientNotes,
    PatientRegistration,
    PatientSearch,
    ShiftingRequest,
)
from care.facility.models.base import covert_choice_dict
from care.facility.models.bed import AssetBed, ConsultationBed
from care.facility.models.patient_base import DISEASE_STATUS_DICT
from care.facility.tasks.patient.discharge_report import generate_discharge_report
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters import CareChoiceFilter, MultiSelectFilter
from care.utils.queryset.patient import get_patient_queryset
from config.authentication import CustomBasicAuthentication, CustomJWTAuthentication, MiddlewareAuthentication

REVERSE_FACILITY_TYPES = covert_choice_dict(FACILITY_TYPES)


class PatientFilterSet(filters.FilterSet):
    source = filters.ChoiceFilter(choices=PatientRegistration.SourceChoices)
    disease_status = CareChoiceFilter(choice_dict=DISEASE_STATUS_DICT)
    facility = filters.UUIDFilter(field_name="facility__external_id")
    facility_type = CareChoiceFilter(field_name="facility__facility_type", choice_dict=REVERSE_FACILITY_TYPES)
    phone_number = filters.CharFilter(field_name="phone_number")
    emergency_phone_number = filters.CharFilter(field_name="emergency_phone_number")
    allow_transfer = filters.BooleanFilter(field_name="allow_transfer")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    ip_no = filters.CharFilter(field_name="last_consultation__ip_no", lookup_expr="icontains")
    gender = filters.NumberFilter(field_name="gender")
    age = filters.NumberFilter(field_name="age")
    age_min = filters.NumberFilter(field_name="age", lookup_expr="gt")
    age_max = filters.NumberFilter(field_name="age", lookup_expr="lt")
    category = filters.ChoiceFilter(field_name="last_consultation__category", choices=CATEGORY_CHOICES)
    created_date = filters.DateFromToRangeFilter(field_name="created_date")
    modified_date = filters.DateFromToRangeFilter(field_name="modified_date")
    srf_id = filters.CharFilter(field_name="srf_id")
    is_declared_positive = filters.BooleanFilter(field_name="is_declared_positive")
    date_declared_positive = filters.DateFromToRangeFilter(field_name="date_declared_positive")
    date_of_result = filters.DateFromToRangeFilter(field_name="date_of_result")
    last_vaccinated_date = filters.DateFromToRangeFilter(field_name="last_vaccinated_date")
    is_antenatal = filters.BooleanFilter(field_name="is_antenatal")
    is_active = filters.BooleanFilter(field_name="is_active")
    # Location Based Filtering
    district = filters.NumberFilter(field_name="district__id")
    district_name = filters.CharFilter(field_name="district__name", lookup_expr="icontains")
    local_body = filters.NumberFilter(field_name="local_body__id")
    local_body_name = filters.CharFilter(field_name="local_body__name", lookup_expr="icontains")
    state = filters.NumberFilter(field_name="state__id")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")
    # Consultation Fields
    is_kasp = filters.BooleanFilter(field_name="last_consultation__is_kasp")
    last_consultation_kasp_enabled_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__kasp_enabled_date"
    )
    last_consultation_admission_date = filters.DateFromToRangeFilter(field_name="last_consultation__admission_date")
    last_consultation_discharge_date = filters.DateFromToRangeFilter(field_name="last_consultation__discharge_date")
    last_consultation_symptoms_onset_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__symptoms_onset_date"
    )
    last_consultation_admitted_to_list = MultiSelectFilter(field_name="last_consultation__admitted_to")
    last_consultation_admitted_to = filters.NumberFilter(field_name="last_consultation__admitted_to")
    last_consultation_assigned_to = filters.NumberFilter(field_name="last_consultation__assigned_to")
    last_consultation_is_telemedicine = filters.BooleanFilter(field_name="last_consultation__is_telemedicine")

    # Vaccination Filters
    covin_id = filters.CharFilter(field_name="covin_id")
    is_vaccinated = filters.BooleanFilter(field_name="is_vaccinated")
    number_of_doses = filters.NumberFilter(field_name="number_of_doses")
    # Permission Filters
    assigned_to = filters.NumberFilter(field_name="assigned_to")
    # Other Filters
    has_bed = filters.BooleanFilter(field_name="has_bed", method='filter_bed_not_null')

    def filter_bed_not_null(self, queryset, name, value):
        return queryset.filter(last_consultation__bed_number__isnull=value, last_consultation__discharge_date__isnull=True)


class PatientDRYFilter(DRYPermissionFiltersBase):
    def filter_queryset(self, request, queryset, view):
        if view.action == "list":
            queryset = self.filter_list_queryset(request, queryset, view)
        if request.user.asset:
            return queryset.filter(
                last_consultation__last_daily_round__bed_id__in=AssetBed.objects.filter(
                    asset=request.user.asset
                ).values("id"),
                last_consultation__last_daily_round__bed__isnull=False,
            )
        if not request.user.is_superuser:
            if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                queryset = queryset.filter(facility__state=request.user.state)
            elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                queryset = queryset.filter(facility__district=request.user.district)
            elif view.action != "transfer":
                allowed_facilities = get_accessible_facilities(request.user)
                q_filters = Q(facility__id__in=allowed_facilities)
                q_filters |= Q(last_consultation__assigned_to=request.user)
                q_filters |= Q(assigned_to=request.user)
                queryset = queryset.filter(q_filters)

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


class PatientViewSet(
    HistoryMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):

    authentication_classes = [CustomBasicAuthentication, CustomJWTAuthentication, MiddlewareAuthentication]
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "external_id"
    queryset = PatientRegistration.objects.all().select_related(
        "local_body",
        "district",
        "state",
        "ward",
        "assigned_to",
        "facility",
        "facility__ward",
        "facility__local_body",
        "facility__district",
        "facility__state",
        # "nearest_facility",
        # "nearest_facility__local_body",
        # "nearest_facility__district",
        # "nearest_facility__state",
        "last_consultation",
        "last_consultation__assigned_to",
        "last_edited",
        "created_by",
    )
    ordering_fields = [
        "id",
        "created_date",
        "modified_date",
        "review_time",
        "date_declared_positive",
    ]

    serializer_class = PatientDetailSerializer
    filter_backends = (
        PatientDRYFilter,
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    )
    filterset_class = PatientFilterSet

    date_range_fields = [
        "created_date",
        "modified_date",
        "date_declared_positive",
        "date_of_result",
        "last_vaccinated_date",
        "last_consultation_admission_date",
        "last_consultation_discharge_date",
        "last_consultation_symptoms_onset_date",
    ]
    CSV_EXPORT_LIMIT = 7

    def get_queryset(self):
        # filter_query = self.request.query_params.get("disease_status")
        queryset = super().get_queryset()
        # if filter_query:
        #     disease_status = filter_query if filter_query.isdigit() else DiseaseStatusEnum[filter_query].value
        #     return queryset.filter(disease_status=disease_status)

        # if self.action == "list":
        #     queryset = queryset.filter(is_active=self.request.GET.get("is_active", True))
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
            # Start Date Validation
            temp = filters.DjangoFilterBackend().get_filterset(self.request, self.queryset, self)
            temp.is_valid()
            within_limits = False
            for field in self.date_range_fields:
                slice_obj = temp.form.cleaned_data.get(field)
                if slice_obj:
                    if not slice_obj.start or not slice_obj.stop:
                        raise ValidationError({field: f"both starting and ending date must be provided for export"})
                    days_difference = (
                        temp.form.cleaned_data.get(field).stop - temp.form.cleaned_data.get(field).start
                    ).days
                    if days_difference <= self.CSV_EXPORT_LIMIT:
                        within_limits = True
                    else:
                        raise ValidationError(
                            {field: f"Cannot export more than {self.CSV_EXPORT_LIMIT} days at a time"}
                        )
            if not within_limits:
                raise ValidationError(
                    {"date": f"Atleast one date field must be filtered to be within {self.CSV_EXPORT_LIMIT} days"}
                )
            # End Date Limiting Validation
            queryset = self.filter_queryset(self.get_queryset()).values(*PatientRegistration.CSV_MAPPING.keys())
            return render_to_csv_response(
                queryset,
                field_header_map=PatientRegistration.CSV_MAPPING,
                field_serializer_map=PatientRegistration.CSV_MAKE_PRETTY,
            )

            # csv_mapping = {
            #     **{f"patient__{key}": value for key, value in PatientRegistration.CSV_MAPPING.items()},
            #     **PatientConsultation.CSV_MAPPING,
            # }
            # csv_make_pretty = {
            #     **{f"patient__{key}": value for key, value in PatientRegistration.CSV_MAKE_PRETTY.items()},
            #     **PatientConsultation.CSV_MAKE_PRETTY,
            # }
            # consultation_qs = PatientConsultation.objects.all()
            # if not request.user.is_superuser:
            #     if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            #         consultation_qs = consultation_qs.filter(patient__facility__state=request.user.state)
            #     elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            #         consultation_qs = consultation_qs.filter(patient__facility__district=request.user.district)
            #     consultation_qs = consultation_qs.filter(
            #         Q(patient__created_by=request.user) | Q(patient__facility__users__id__exact=request.user.id)
            #     ).distinct("id")
            # consultation_qs = (
            #     consultation_qs.order_by("patient__external_id", "-id")
            #     .distinct("patient__external_id")
            #     .select_related(
            #         "patient",
            #         "patient__facility",
            #         "patient__nearest_facility",
            #         "patient__local_body",
            #         "patient__district",
            #         "patient__state",
            #     )
            #     .annotate(consultation_created_date=F("created_date"))
            #     .values(*csv_mapping)
            # )

            # patient_without_consultation_qs = (
            #     self.get_queryset()
            #     .filter(consultations__isnull=True)
            #     .annotate(
            #         **{f"patient__{key}": F(key) for key in PatientRegistration.CSV_MAPPING.keys()},
            #         **{
            #             key: Value(*defaults)
            #             for key, defaults in PatientConsultation.CSV_DATATYPE_DEFAULT_MAPPING.items()
            #         },
            #     )
            #     .annotate(consultation_created_date=Value(None, DateTimeField()))
            #     .select_related(
            #         "facility", "nearest_facility", "facility__local_body", "facility__district", "facility__state",
            #     )
            #     .values(*csv_mapping)
            # )
            # queryset = consultation_qs.union(patient_without_consultation_qs)
            # return render_to_csv_response(queryset, field_header_map=csv_mapping, field_serializer_map=csv_make_pretty,)

        return super(PatientViewSet, self).list(request, *args, **kwargs)

    @action(detail=True, methods=["POST"])
    def discharge_patient(self, request, *args, **kwargs):
        discharged = bool(request.data.get("discharge", False))
        patient = self.get_object()
        patient.is_active = discharged
        patient.allow_transfer = not discharged
        patient.save(update_fields=["allow_transfer", "is_active"])
        last_consultation = PatientConsultation.objects.filter(patient=patient).order_by("-id").first()
        current_time = localtime(now())
        if last_consultation:
            if last_consultation.discharge_date is None:
                last_consultation.discharge_date = current_time
                last_consultation.save()
            ConsultationBed.objects.filter(consultation=last_consultation, end_date__isnull=True).update(
                end_date=current_time
            )

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def discharge_summary(self, request, *args, **kwargs):
        patient = self.get_object()
        email = request.data.get("email", "")
        try:
            validate_email(email)
        except Exception:
            email = request.user.email
        generate_discharge_report.delay(patient.id, email)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        patient = PatientRegistration.objects.get(
            id=PatientSearch.objects.get(external_id=kwargs["external_id"]).patient_id
        )

        if patient.allow_transfer is False:
            return Response(
                {"Patient": "Cannot Transfer Patient , Source Facility Does Not Allow"},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        patient.is_active = True
        patient.allow_transfer = False
        serializer = self.get_serializer_class()(patient, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        patient = PatientRegistration.objects.get(
            id=PatientSearch.objects.get(external_id=kwargs["external_id"]).patient_id
        )
        response_serializer = self.get_serializer_class()(patient)
        # Update all Active Shifting Request to Rejected

        for shifting_request in ShiftingRequest.objects.filter(~Q(status__in=[30, 50, 80]), patient=patient):
            shifting_request.status = 30
            shifting_request.comments = (
                shifting_request.comments
                + f"\n The shifting request was auto rejected by the system as the patient was moved to {patient.facility.name}"
            )
            shifting_request.save(update_fields=["status", "comments"])
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)


class FacilityPatientStatsHistoryFilterSet(filters.FilterSet):
    entry_date = filters.DateFromToRangeFilter(field_name="entry_date")


class FacilityPatientStatsHistoryViewSet(viewsets.ModelViewSet):
    lookup_field = "external_id"
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = FacilityPatientStatsHistory.objects.filter(facility__deleted=False).order_by("-entry_date")
    serializer_class = FacilityPatientStatsHistorySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityPatientStatsHistoryFilterSet
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(facility__external_id=self.kwargs.get("facility_external_id"))
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
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


class PatientSearchSetPagination(PageNumberPagination):
    page_size = 200


class PatientSearchViewSet(UserAccessMixin, ListModelMixin, GenericViewSet):
    http_method_names = ["get"]
    queryset = PatientSearch.objects.all()
    serializer_class = PatientSearchSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    pagination_class = PatientSearchSetPagination

    def get_queryset(self):
        if self.action != "list":
            return super(PatientSearchViewSet, self).get_queryset()
        else:
            serializer = PatientSearchSerializer(data=self.request.query_params, partial=True)
            serializer.is_valid(raise_exception=True)
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                search_keys = [
                    "date_of_birth",
                    "year_of_birth",
                    "phone_number",
                    "name",
                    "age",
                ]
            else:
                search_keys = ["date_of_birth", "year_of_birth", "phone_number", "age"]
            search_fields = {
                key: serializer.validated_data[key] for key in search_keys if serializer.validated_data.get(key)
            }
            if not search_fields:
                raise serializers.ValidationError(
                    {"detail": [f"None of the search keys provided. Available: {', '.join(search_keys)}"]}
                )

            # if not self.request.user.is_superuser:
            #     search_fields["state_id"] = self.request.user.state_id

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


class PatientNotesViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = PatientNotes.objects.all().select_related("facility", "patient", "created_by").order_by("-created_date")
    serializer_class = PatientNotesSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(patient__external_id=self.kwargs.get("patient_external_id"))
        if not user.is_superuser:
            return queryset
        if user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(patient__facility__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(patient__facility__district=user.district)
        else:
            allowed_facilities = get_accessible_facilities(user)
            q_filters = Q(patient__facility__id__in=allowed_facilities)
            q_filters |= Q(patient__last_consultation__assigned_to=user)
            q_filters |= Q(patient__assigned_to=user)
            queryset = queryset.filter(q_filters)
        return queryset

    def perform_create(self, serializer):
        patient = get_object_or_404(
            get_patient_queryset(self.request.user).filter(external_id=self.kwargs.get("patient_external_id"))
        )
        if not patient.is_active:
            raise ValidationError({"patient": "Only active patients data can be updated"})
        return serializer.save(facility=patient.facility, patient=patient, created_by=self.request.user)
