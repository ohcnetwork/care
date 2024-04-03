import datetime
import json
from json import JSONDecodeError

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db import models
from django.db.models import (
    Case,
    ExpressionWrapper,
    F,
    Func,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, ExtractDay, Now
from django.db.models.query import QuerySet
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from drf_spectacular.utils import extend_schema, extend_schema_view
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient import (
    FacilityPatientStatsHistorySerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientNotesEditSerializer,
    PatientNotesSerializer,
    PatientSearchSerializer,
    PatientTransferSerializer,
)
from care.facility.api.serializers.patient_icmr import PatientICMRSerializer
from care.facility.api.viewsets.mixins.history import HistoryMixin
from care.facility.events.handler import create_consultation_events
from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    DISCHARGE_REASON_CHOICES,
    FACILITY_TYPES,
    BedTypeChoices,
    DailyRound,
    Facility,
    FacilityPatientStatsHistory,
    PatientNotes,
    PatientRegistration,
    ShiftingRequest,
)
from care.facility.models.base import covert_choice_dict
from care.facility.models.bed import AssetBed
from care.facility.models.icd11_diagnosis import (
    INACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConditionVerificationStatus,
)
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientNotesEdit
from care.facility.models.patient_base import (
    DISEASE_STATUS_DICT,
    NewDischargeReasonEnum,
)
from care.users.models import User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters.choicefilter import CareChoiceFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.patient import get_patient_notes_queryset
from config.authentication import (
    CustomBasicAuthentication,
    CustomJWTAuthentication,
    MiddlewareAuthentication,
)

REVERSE_FACILITY_TYPES = covert_choice_dict(FACILITY_TYPES)
REVERSE_BED_TYPES = covert_choice_dict(BedTypeChoices)
DISCHARGE_REASONS = [choice[0] for choice in DISCHARGE_REASON_CHOICES]
VENTILATOR_CHOICES = covert_choice_dict(DailyRound.VentilatorInterfaceChoice)


class PatientFilterSet(filters.FilterSet):
    source = filters.ChoiceFilter(choices=PatientRegistration.SourceChoices)
    disease_status = CareChoiceFilter(choice_dict=DISEASE_STATUS_DICT)
    facility = filters.UUIDFilter(field_name="facility__external_id")
    facility_type = CareChoiceFilter(
        field_name="facility__facility_type",
        choice_dict=REVERSE_FACILITY_TYPES,
    )
    phone_number = filters.CharFilter(field_name="phone_number")
    emergency_phone_number = filters.CharFilter(field_name="emergency_phone_number")
    allow_transfer = filters.BooleanFilter(field_name="allow_transfer")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    patient_no = filters.CharFilter(
        field_name="last_consultation__patient_no", lookup_expr="icontains"
    )
    gender = filters.NumberFilter(field_name="gender")
    age = filters.NumberFilter(field_name="age")
    age_min = filters.NumberFilter(field_name="age", lookup_expr="gte")
    age_max = filters.NumberFilter(field_name="age", lookup_expr="lte")
    deprecated_covid_category = filters.ChoiceFilter(
        field_name="last_consultation__deprecated_covid_category",
        choices=COVID_CATEGORY_CHOICES,
    )
    category = filters.ChoiceFilter(
        method="filter_by_category",
        choices=CATEGORY_CHOICES,
    )

    def filter_by_category(self, queryset, name, value):
        if value:
            queryset = queryset.filter(
                (
                    Q(last_consultation__last_daily_round__isnull=False)
                    & Q(last_consultation__last_daily_round__patient_category=value)
                )
                | (
                    Q(last_consultation__last_daily_round__isnull=True)
                    & Q(last_consultation__category=value)
                )
            )
        return queryset

    created_date = filters.DateFromToRangeFilter(field_name="created_date")
    modified_date = filters.DateFromToRangeFilter(field_name="modified_date")
    srf_id = filters.CharFilter(field_name="srf_id")
    is_declared_positive = filters.BooleanFilter(field_name="is_declared_positive")
    date_declared_positive = filters.DateFromToRangeFilter(
        field_name="date_declared_positive"
    )
    date_of_result = filters.DateFromToRangeFilter(field_name="date_of_result")
    last_vaccinated_date = filters.DateFromToRangeFilter(
        field_name="last_vaccinated_date"
    )
    is_antenatal = filters.BooleanFilter(field_name="is_antenatal")
    last_menstruation_start_date = filters.DateFromToRangeFilter(
        field_name="last_menstruation_start_date"
    )
    date_of_delivery = filters.DateFromToRangeFilter(field_name="date_of_delivery")
    is_active = filters.BooleanFilter(field_name="is_active")
    # Location Based Filtering
    district = filters.NumberFilter(field_name="district__id")
    district_name = filters.CharFilter(
        field_name="district__name", lookup_expr="icontains"
    )
    local_body = filters.NumberFilter(field_name="local_body__id")
    local_body_name = filters.CharFilter(
        field_name="local_body__name", lookup_expr="icontains"
    )
    state = filters.NumberFilter(field_name="state__id")
    state_name = filters.CharFilter(field_name="state__name", lookup_expr="icontains")
    # Consultation Fields
    is_kasp = filters.BooleanFilter(field_name="last_consultation__is_kasp")
    last_consultation_kasp_enabled_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__kasp_enabled_date"
    )
    last_consultation_encounter_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__encounter_date"
    )
    last_consultation_discharge_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__discharge_date"
    )
    last_consultation_symptoms_onset_date = filters.DateFromToRangeFilter(
        field_name="last_consultation__symptoms_onset_date"
    )
    last_consultation_admitted_bed_type_list = MultiSelectFilter(
        method="filter_by_bed_type",
    )
    last_consultation_medico_legal_case = filters.BooleanFilter(
        field_name="last_consultation__medico_legal_case"
    )
    last_consultation_current_bed__location = filters.UUIDFilter(
        field_name="last_consultation__current_bed__bed__location__external_id"
    )

    def filter_by_bed_type(self, queryset, name, value):
        if not value:
            return queryset

        values = value.split(",")
        filter_q = Q()

        if "None" in values:
            filter_q |= Q(last_consultation__current_bed__isnull=True)
            values.remove("None")
        if values:
            filter_q |= Q(last_consultation__current_bed__bed__bed_type__in=values)

        return queryset.filter(filter_q)

    last_consultation_admitted_bed_type = CareChoiceFilter(
        field_name="last_consultation__current_bed__bed__bed_type",
        choice_dict=REVERSE_BED_TYPES,
    )
    last_consultation__new_discharge_reason = filters.ChoiceFilter(
        field_name="last_consultation__new_discharge_reason",
        choices=NewDischargeReasonEnum.choices,
    )
    last_consultation_assigned_to = filters.NumberFilter(
        field_name="last_consultation__assigned_to"
    )
    last_consultation_is_telemedicine = filters.BooleanFilter(
        field_name="last_consultation__is_telemedicine"
    )
    ventilator_interface = CareChoiceFilter(
        field_name="last_consultation__last_daily_round__ventilator_interface",
        choice_dict=VENTILATOR_CHOICES,
    )

    # Vaccination Filters
    covin_id = filters.CharFilter(field_name="covin_id")
    is_vaccinated = filters.BooleanFilter(field_name="is_vaccinated")
    number_of_doses = filters.NumberFilter(field_name="number_of_doses")
    # Permission Filters
    assigned_to = filters.NumberFilter(field_name="assigned_to")
    # Other Filters
    has_bed = filters.BooleanFilter(field_name="has_bed", method="filter_bed_not_null")

    def filter_bed_not_null(self, queryset, name, value):
        return queryset.filter(
            last_consultation__bed_number__isnull=value,
            last_consultation__discharge_date__isnull=True,
        )

    # Filter consultations by ICD-11 Diagnoses
    diagnoses = MultiSelectFilter(method="filter_by_diagnoses")
    diagnoses_unconfirmed = MultiSelectFilter(method="filter_by_diagnoses")
    diagnoses_provisional = MultiSelectFilter(method="filter_by_diagnoses")
    diagnoses_differential = MultiSelectFilter(method="filter_by_diagnoses")
    diagnoses_confirmed = MultiSelectFilter(method="filter_by_diagnoses")

    def filter_by_diagnoses(self, queryset, name, value):
        if not value:
            return queryset
        filter_q = Q(last_consultation__diagnoses__diagnosis_id__in=value.split(","))
        if name == "diagnoses":
            filter_q &= ~Q(
                last_consultation__diagnoses__verification_status__in=INACTIVE_CONDITION_VERIFICATION_STATUSES
            )
        else:
            verification_status = {
                "diagnoses_unconfirmed": ConditionVerificationStatus.UNCONFIRMED,
                "diagnoses_provisional": ConditionVerificationStatus.PROVISIONAL,
                "diagnoses_differential": ConditionVerificationStatus.DIFFERENTIAL,
                "diagnoses_confirmed": ConditionVerificationStatus.CONFIRMED,
            }[name]
            filter_q &= Q(
                last_consultation__diagnoses__verification_status=verification_status
            )
        return queryset.filter(filter_q)


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
                if view.action == "retrieve":
                    q_filters |= Q(consultations__facility__id__in=allowed_facilities)
                q_filters |= Q(last_consultation__assigned_to=request.user)
                q_filters |= Q(assigned_to=request.user)
                queryset = queryset.filter(q_filters)
        return queryset

    def filter_list_queryset(self, request, queryset, view):
        try:
            show_without_facility = json.loads(
                request.query_params.get("without_facility")
            )
        except (
            JSONDecodeError,
            TypeError,
        ):
            show_without_facility = False
        return queryset.filter(facility_id__isnull=show_without_facility)


class PatientCustomOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get("ordering", "")

        if ordering == "category_severity" or ordering == "-category_severity":
            category_ordering = {
                category: index + 1
                for index, (category, _) in enumerate(CATEGORY_CHOICES)
            }
            when_statements = [
                When(last_consultation__category=cat, then=order)
                for cat, order in category_ordering.items()
            ]
            queryset = queryset.annotate(
                category_severity=Case(
                    *when_statements,
                    default=(len(category_ordering) + 1),
                    output_field=models.IntegerField(),
                )
            ).order_by(ordering)

        return queryset.distinct(ordering.lstrip("-") if ordering else "id")


@extend_schema_view(history=extend_schema(tags=["patient"]))
class PatientViewSet(
    HistoryMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    authentication_classes = [
        CustomBasicAuthentication,
        CustomJWTAuthentication,
        MiddlewareAuthentication,
    ]
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "external_id"
    queryset = (
        PatientRegistration.objects.all()
        .select_related(
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
        .annotate(
            coalesced_dob=Coalesce(
                "date_of_birth",
                Func(
                    F("year_of_birth"),
                    Value(1),
                    Value(1),
                    function="MAKE_DATE",
                    output_field=models.DateField(),
                ),
                output_field=models.DateField(),
            ),
            age_end=Case(
                When(death_datetime__isnull=True, then=Now()),
                default=F("death_datetime__date"),
            ),
        )
        .annotate(
            age=Func(
                Value("year"),
                Func(
                    F("age_end"),
                    F("coalesced_dob"),
                    function="age",
                ),
                function="date_part",
                output_field=models.IntegerField(),
            ),
            age_days=ExpressionWrapper(
                ExtractDay(F("age_end") - F("coalesced_dob")),
                output_field=models.IntegerField(),
            ),
        )
    )
    ordering_fields = [
        "facility__name",
        "id",
        "name",
        "created_date",
        "modified_date",
        "review_time",
        "last_consultation__current_bed__bed__name",
        "date_declared_positive",
    ]

    serializer_class = PatientDetailSerializer
    filter_backends = (
        PatientDRYFilter,
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
        PatientCustomOrderingFilter,
    )
    filterset_class = PatientFilterSet

    date_range_fields = [
        "created_date",
        "modified_date",
        "date_declared_positive",
        "date_of_result",
        "last_vaccinated_date",
        "last_consultation_encounter_date",
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

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        if self.action == "list" and settings.CSV_REQUEST_PARAMETER in self.request.GET:
            for backend in (PatientDRYFilter, filters.DjangoFilterBackend):
                queryset = backend().filter_queryset(self.request, queryset, self)
            is_active = self.request.GET.get("is_active", "False") == "True"
            return queryset.filter(last_consultation__discharge_date__isnull=is_active)

        return super().filter_queryset(queryset)

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
            temp = filters.DjangoFilterBackend().get_filterset(
                self.request, self.queryset, self
            )
            temp.is_valid()
            within_limits = False
            for field in self.date_range_fields:
                slice_obj = temp.form.cleaned_data.get(field)
                if slice_obj:
                    if not slice_obj.start or not slice_obj.stop:
                        raise ValidationError(
                            {
                                field: "both starting and ending date must be provided for export"
                            }
                        )
                    days_difference = (
                        temp.form.cleaned_data.get(field).stop
                        - temp.form.cleaned_data.get(field).start
                    ).days
                    if days_difference <= self.CSV_EXPORT_LIMIT:
                        within_limits = True
                    else:
                        raise ValidationError(
                            {
                                field: f"Cannot export more than {self.CSV_EXPORT_LIMIT} days at a time"
                            }
                        )
            if not within_limits:
                raise ValidationError(
                    {
                        "date": f"Atleast one date field must be filtered to be within {self.CSV_EXPORT_LIMIT} days"
                    }
                )
            # End Date Limiting Validation
            queryset = (
                self.filter_queryset(self.get_queryset())
                .annotate(**PatientRegistration.CSV_ANNOTATE_FIELDS)
                .values(*PatientRegistration.CSV_MAPPING.keys())
            )
            return render_to_csv_response(
                queryset,
                field_header_map=PatientRegistration.CSV_MAPPING,
                field_serializer_map=PatientRegistration.CSV_MAKE_PRETTY,
            )

        return super(PatientViewSet, self).list(request, *args, **kwargs)

    @extend_schema(tags=["patient"])
    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        patient = PatientRegistration.objects.get(external_id=kwargs["external_id"])
        facility = Facility.objects.get(external_id=request.data["facility"])

        if patient.is_active and facility == patient.facility:
            return Response(
                {
                    "Patient": "Patient transfer cannot be completed because the patient has an active consultation in the same facility"
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        if patient.allow_transfer is False:
            return Response(
                {
                    "Patient": "Patient transfer cannot be completed because the source facility does not permit it"
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        patient.allow_transfer = False
        patient.is_active = True
        serializer = self.get_serializer_class()(patient, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        patient = PatientRegistration.objects.get(external_id=kwargs["external_id"])
        response_serializer = self.get_serializer(patient)
        # Update all Active Shifting Request to Rejected

        for shifting_request in ShiftingRequest.objects.filter(
            ~Q(status__in=[30, 50, 80]), patient=patient
        ):
            shifting_request.status = 30
            shifting_request.comments = f"{shifting_request.comments}\n The shifting request was auto rejected by the system as the patient was moved to {patient.facility.name}"
            shifting_request.save(update_fields=["status", "comments"])
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)


class FacilityDischargedPatientFilterSet(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


@extend_schema_view(tags=["patient"])
class FacilityDischargedPatientViewSet(GenericViewSet, mixins.ListModelMixin):
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "external_id"
    serializer_class = PatientListSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityDischargedPatientFilterSet
    queryset = PatientRegistration.objects.select_related(
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
        "last_consultation",
        "last_consultation__assigned_to",
        "last_edited",
        "created_by",
    )

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        return qs.filter(
            Q(consultations__facility__external_id=self.kwargs["facility_external_id"])
            & Q(consultations__discharge_date__isnull=False)
        ).distinct()


class FacilityPatientStatsHistoryFilterSet(filters.FilterSet):
    entry_date = filters.DateFromToRangeFilter(field_name="entry_date")


class FacilityPatientStatsHistoryViewSet(viewsets.ModelViewSet):
    lookup_field = "external_id"
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = FacilityPatientStatsHistory.objects.filter(
        facility__deleted=False
    ).order_by("-entry_date")
    serializer_class = FacilityPatientStatsHistorySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilityPatientStatsHistoryFilterSet
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(
            facility__external_id=self.kwargs.get("facility_external_id")
        )
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
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
        return serializer.save(facility=self.get_facility())

    def list(self, request, *args, **kwargs):
        """
        Patient Stats - List

        Available Filters
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date
        - entry_date_before: date in YYYY-MM-DD format, inclusive of this date

        """
        return super(FacilityPatientStatsHistoryViewSet, self).list(
            request, *args, **kwargs
        )


class PatientSearchSetPagination(PageNumberPagination):
    page_size = 200


class PatientSearchViewSet(ListModelMixin, GenericViewSet):
    http_method_names = ["get"]
    queryset = PatientRegistration.objects.only(
        "id",
        "external_id",
        "name",
        "gender",
        "phone_number",
        "state_id",
        "facility",
        "allow_transfer",
        "is_active",
    )
    serializer_class = PatientSearchSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    pagination_class = PatientSearchSetPagination

    def get_queryset(self):
        if self.action != "list":
            return super(PatientSearchViewSet, self).get_queryset()
        else:
            serializer = PatientSearchSerializer(
                data=self.request.query_params, partial=True
            )
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
                search_keys = [
                    "date_of_birth",
                    "year_of_birth",
                    "phone_number",
                    "age",
                ]
            search_fields = {
                key: serializer.validated_data[key]
                for key in search_keys
                if serializer.validated_data.get(key)
            }
            if not search_fields:
                raise serializers.ValidationError(
                    {
                        "detail": [
                            f"None of the search keys provided. Available: {', '.join(search_keys)}"
                        ]
                    }
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

    @extend_schema(tags=["patient"])
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


class PatientNotesFilterSet(filters.FilterSet):
    consultation = filters.CharFilter(field_name="consultation__external_id")


class PatientNotesEditViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = PatientNotesEdit.objects.all().order_by("-edited_date")
    lookup_field = "external_id"
    serializer_class = PatientNotesEditSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user

        queryset = self.queryset.filter(
            patient_note__external_id=self.kwargs.get("notes_external_id")
        )

        if user.is_superuser:
            return queryset
        if user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(
                patient_note__patient__facility__state=user.state
            )
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(
                patient_note__patient__facility__district=user.district
            )
        else:
            allowed_facilities = get_accessible_facilities(user)
            q_filters = Q(patient_note__patient__facility__id__in=allowed_facilities)
            q_filters |= Q(patient_note__patient__last_consultation__assigned_to=user)
            q_filters |= Q(patient_note__patient__assigned_to=user)
            q_filters |= Q(patient_note__created_by=user)
            queryset = queryset.filter(q_filters)

        return queryset


class PatientNotesViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    queryset = (
        PatientNotes.objects.all()
        .select_related("facility", "patient", "created_by")
        .order_by("-created_date")
    )
    lookup_field = "external_id"
    serializer_class = PatientNotesSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = PatientNotesFilterSet

    def get_queryset(self):
        user = self.request.user

        last_edit_subquery = PatientNotesEdit.objects.filter(
            patient_note=OuterRef("pk")
        ).order_by("-edited_date")

        queryset = self.queryset.filter(
            patient__external_id=self.kwargs.get("patient_external_id")
        ).annotate(
            last_edited_by=Subquery(
                last_edit_subquery.values("edited_by__username")[:1]
            ),
            last_edited_date=Subquery(last_edit_subquery.values("edited_date")[:1]),
        )

        if user.is_superuser:
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
            q_filters |= Q(created_by=user)
            queryset = queryset.filter(q_filters)

        return queryset

    def perform_create(self, serializer):
        patient = get_object_or_404(
            get_patient_notes_queryset(self.request.user).filter(
                external_id=self.kwargs.get("patient_external_id")
            )
        )
        if not patient.is_active:
            raise ValidationError(
                {"patient": "Updating patient data is only allowed for active patients"}
            )

        instance: PatientNotes = serializer.save(
            facility=patient.facility,
            patient=patient,
            consultation=patient.last_consultation,
            created_by=self.request.user,
        )

        create_consultation_events(
            instance.consultation_id,
            instance,
            self.request.user.id,
            instance.created_date,
        )

        message = {
            "facility_id": str(patient.facility.external_id),
            "patient_id": str(patient.external_id),
            "from": "patient/doctor_notes/create",
        }

        NotificationGenerator(
            event=Notification.Event.PUSH_MESSAGE,
            caused_by=self.request.user,
            caused_object=instance,
            message=message,
            facility=patient.facility,
            generate_for_facility=True,
        ).generate()

        NotificationGenerator(
            event=Notification.Event.PATIENT_NOTE_ADDED,
            caused_by=self.request.user,
            caused_object=instance,
            facility=patient.facility,
            generate_for_facility=True,
        ).generate()

        return instance

    def perform_update(self, serializer):
        user = self.request.user
        patient = get_object_or_404(
            get_patient_notes_queryset(self.request.user).filter(
                external_id=self.kwargs.get("patient_external_id")
            )
        )

        if not patient.is_active:
            raise ValidationError(
                {"patient": "Updating patient data is only allowed for active patients"}
            )

        if serializer.instance.created_by != user:
            raise ValidationError(
                {"Note": "Only the user who created the note can edit it"}
            )

        return super().perform_update(serializer)
