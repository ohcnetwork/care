import json
from json import JSONDecodeError

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.validators import MaxValueValidator, MinValueValidator
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
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, serializers, status
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
    PatientDetailSerializer,
    PatientListSerializer,
    PatientNotesEditSerializer,
    PatientNotesSerializer,
    PatientSearchSerializer,
    PatientTransferSerializer,
)
from care.facility.api.serializers.patient_icmr import PatientICMRSerializer
from care.facility.api.viewsets.mixins.history import HistoryMixin
from care.facility.models import (
    CATEGORY_CHOICES,
    COVID_CATEGORY_CHOICES,
    DISCHARGE_REASON_CHOICES,
    FACILITY_TYPES,
    BedTypeChoices,
    DailyRound,
    Facility,
    PatientNotes,
    PatientNoteThreadChoices,
    PatientRegistration,
    ShiftingRequest,
)
from care.facility.models.base import covert_choice_dict
from care.facility.models.bed import AssetBed, ConsultationBed
from care.facility.models.icd11_diagnosis import (
    INACTIVE_CONDITION_VERIFICATION_STATUSES,
    ConditionVerificationStatus,
)
from care.facility.models.notification import Notification
from care.facility.models.patient import PatientNotesEdit, RationCardCategory
from care.facility.models.patient_base import (
    DISEASE_STATUS_DICT,
    NewDischargeReasonEnum,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import GENDER_CHOICES, User
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.exports.mixins import CSVExportViewSetMixin
from care.utils.filters.choicefilter import CareChoiceFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.patient import get_patient_notes_queryset
from config.authentication import (
    CustomBasicAuthentication,
    CustomJWTAuthentication,
    MiddlewareAssetAuthentication,
)

REVERSE_FACILITY_TYPES = covert_choice_dict(FACILITY_TYPES)
REVERSE_BED_TYPES = covert_choice_dict(BedTypeChoices)
DISCHARGE_REASONS = [choice[0] for choice in DISCHARGE_REASON_CHOICES]


class PatientFilterSet(filters.FilterSet):
    last_consultation_field = "last_consultation"

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
    name = filters.CharFilter(
        field_name="name", lookup_expr="icontains", max_length=200
    )
    patient_no = filters.CharFilter(
        field_name=f"{last_consultation_field}__patient_no",
        lookup_expr="iexact",
        max_length=100,
    )
    gender = filters.ChoiceFilter(field_name="gender", choices=GENDER_CHOICES)
    age = filters.NumberFilter(field_name="age", validators=[MinValueValidator(0)])
    age_min = filters.NumberFilter(
        field_name="age", lookup_expr="gte", validators=[MinValueValidator(0)]
    )
    age_max = filters.NumberFilter(
        field_name="age", lookup_expr="lte", validators=[MinValueValidator(0)]
    )
    deprecated_covid_category = filters.ChoiceFilter(
        field_name=f"{last_consultation_field}__deprecated_covid_category",
        choices=COVID_CATEGORY_CHOICES,
    )
    category = filters.ChoiceFilter(
        method="filter_by_category",
        choices=CATEGORY_CHOICES,
    )
    ration_card_category = filters.ChoiceFilter(choices=RationCardCategory.choices)

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
    srf_id = filters.CharFilter(field_name="srf_id", max_length=200)
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
        field_name="district__name", lookup_expr="icontains", max_length=255
    )
    local_body = filters.NumberFilter(field_name="local_body__id")
    local_body_name = filters.CharFilter(
        field_name="local_body__name", lookup_expr="icontains", max_length=255
    )
    state = filters.NumberFilter(field_name="state__id")
    state_name = filters.CharFilter(
        field_name="state__name", lookup_expr="icontains", max_length=255
    )
    # Consultation Fields
    is_kasp = filters.BooleanFilter(field_name=f"{last_consultation_field}__is_kasp")
    last_consultation_kasp_enabled_date = filters.DateFromToRangeFilter(
        field_name=f"{last_consultation_field}__kasp_enabled_date"
    )
    last_consultation_encounter_date = filters.DateFromToRangeFilter(
        field_name=f"{last_consultation_field}__encounter_date"
    )
    last_consultation_discharge_date = filters.DateFromToRangeFilter(
        field_name=f"{last_consultation_field}__discharge_date"
    )
    last_consultation_admitted_bed_type_list = MultiSelectFilter(
        method="filter_by_bed_type",
    )
    last_consultation_medico_legal_case = filters.BooleanFilter(
        field_name=f"{last_consultation_field}__medico_legal_case"
    )
    last_consultation_current_bed__location = filters.UUIDFilter(
        field_name=f"{last_consultation_field}__current_bed__bed__location__external_id"
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
        field_name=f"{last_consultation_field}__current_bed__bed__bed_type",
        choice_dict=REVERSE_BED_TYPES,
    )
    last_consultation__new_discharge_reason = filters.ChoiceFilter(
        field_name=f"{last_consultation_field}__new_discharge_reason",
        choices=NewDischargeReasonEnum.choices,
    )
    last_consultation_assigned_to = filters.NumberFilter(
        field_name=f"{last_consultation_field}__assigned_to"
    )
    last_consultation_is_telemedicine = filters.BooleanFilter(
        field_name=f"{last_consultation_field}__is_telemedicine"
    )
    ventilator_interface = CareChoiceFilter(
        field_name=f"{last_consultation_field}__last_daily_round__ventilator_interface",
        choice_dict={
            label: value for value, label in DailyRound.VentilatorInterfaceType.choices
        },
    )

    # Vaccination Filters
    covin_id = filters.CharFilter(field_name="covin_id", max_length=15)
    is_vaccinated = filters.BooleanFilter(field_name="is_vaccinated")
    number_of_doses = filters.NumberFilter(
        field_name="number_of_doses",
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )
    # Permission Filters
    assigned_to = filters.NumberFilter(field_name="assigned_to")
    # Other Filters
    has_bed = filters.BooleanFilter(field_name="has_bed", method="filter_bed_not_null")

    def filter_bed_not_null(self, queryset, name, value):
        return queryset.filter(
            last_consultation__bed_number__isnull=value,
            last_consultation__discharge_date__isnull=True,
        )

    def filter_by_review_missed(self, queryset, name, value):
        if isinstance(value, bool):
            if value:
                queryset = queryset.filter(
                    Q(review_time__isnull=False) & Q(review_time__lt=timezone.now())
                )
            else:
                queryset = queryset.filter(
                    Q(review_time__isnull=True) | Q(review_time__gt=timezone.now())
                )
        return queryset

    review_missed = filters.BooleanFilter(method="filter_by_review_missed")

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

    last_consultation__consent_types = MultiSelectFilter(
        method="filter_by_has_consents"
    )

    def filter_by_has_consents(self, queryset, name, value: str):
        if not value:
            return queryset

        values = value.split(",")

        filter_q = Q()

        if "None" in values:
            filter_q |= ~Q(
                last_consultation__has_consents__len__gt=0,
            )
            values.remove("None")

        if values:
            filter_q |= Q(
                last_consultation__has_consents__overlap=values,
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
                    q_filters |= Q(
                        id__in=PatientConsultation.objects.filter(
                            facility__id__in=allowed_facilities
                        ).values("patient_id")
                    )
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

        if ordering in ("category_severity", "-category_severity"):
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

        return queryset


@extend_schema_view(history=extend_schema(tags=["patient"]))
class PatientViewSet(
    CSVExportViewSetMixin,
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
        MiddlewareAssetAuthentication,
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
    ]

    def get_queryset(self):
        queryset = super().get_queryset().order_by("modified_date")

        if self.action == "list":
            queryset = queryset.annotate(
                no_consultation_filed=Case(
                    When(
                        Q(last_consultation__isnull=True)
                        | ~Q(last_consultation__facility__id=F("facility__id"))
                        | (
                            Q(last_consultation__discharge_date__isnull=False)
                            & Q(is_active=True)
                        ),
                        then=True,
                    ),
                    default=False,
                    output_field=models.BooleanField(),
                )
            ).order_by(
                "-no_consultation_filed",
                "-modified_date",
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        if self.action == "icmr_sample":
            return PatientICMRSerializer
        if self.action == "transfer":
            return PatientTransferSerializer
        return self.serializer_class

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        if self.action == "list" and settings.CSV_REQUEST_PARAMETER in self.request.GET:
            for backend in (PatientDRYFilter, filters.DjangoFilterBackend):
                queryset = backend().filter_queryset(self.request, queryset, self)
            is_active = self.request.GET.get("is_active", "False") == "True"
            return queryset.filter(last_consultation__discharge_date__isnull=is_active)

        return super().filter_queryset(queryset)

    @extend_schema(tags=["patient"])
    @action(detail=True, methods=["POST"])
    def transfer(self, request, *args, **kwargs):
        patient = PatientRegistration.objects.get(external_id=kwargs["external_id"])
        facility = get_object_or_404(Facility, external_id=request.data["facility"])

        if patient.is_expired:
            return Response(
                {
                    "Patient": "Patient transfer cannot be completed because the patient is expired"
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

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


class DischargePatientFilterSet(PatientFilterSet):
    last_consultation_field = "last_discharge_consultation"

    # Filters patients by the type of bed they have been assigned to.
    def filter_by_bed_type(self, queryset, name, value):
        if not value:
            return queryset

        values = value.split(",")
        filter_q = Q()

        # Get the latest consultation bed records for each patient by ordering by patient_id
        # and the end_date of the consultation, then selecting distinct patient entries.
        last_consultation_bed_ids = (
            ConsultationBed.objects.filter(end_date__isnull=False)
            .order_by("consultation__patient_id", "-end_date")
            .distinct("consultation__patient_id")
        )

        # patients whose last consultation did not include a bed
        if "None" in values:
            filter_q |= ~Q(
                last_discharge_consultation__id__in=Subquery(
                    last_consultation_bed_ids.values_list("consultation_id", flat=True)
                )
            )
            values.remove("None")

        # If the values list contains valid bed types, apply the filtering for those bed types.
        if isinstance(values, list) and len(values) > 0:
            filter_q |= Q(
                last_discharge_consultation__id__in=Subquery(
                    ConsultationBed.objects.filter(
                        id__in=Subquery(
                            last_consultation_bed_ids.values_list("id", flat=True)
                        ),  # Filter by consultation beds that are part of the latest records for each patient.
                        bed__bed_type__in=values,  # Match the bed types from the provided values list.
                    ).values_list("consultation_id", flat=True)
                )
            )

        return queryset.filter(filter_q)


@extend_schema_view(tags=["patient"])
class FacilityDischargedPatientViewSet(
    CSVExportViewSetMixin, GenericViewSet, mixins.ListModelMixin
):
    permission_classes = (IsAuthenticated, DRYPermissions)
    lookup_field = "external_id"
    serializer_class = PatientListSerializer
    filter_backends = (
        PatientDRYFilter,
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
        PatientCustomOrderingFilter,
    )
    filterset_class = DischargePatientFilterSet
    queryset = (
        PatientRegistration.objects.annotate(
            last_discharge_consultation__id=Subquery(
                PatientConsultation.objects.filter(
                    patient_id=OuterRef("id"),
                    discharge_date__isnull=False,
                )
                .order_by("-discharge_date")
                .values("id")[:1]
            )
        )
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

    date_range_fields = [
        "created_date",
        "modified_date",
        "date_declared_positive",
        "date_of_result",
        "last_vaccinated_date",
        "last_discharge_consultation_encounter_date",
        "last_discharge_consultation_discharge_date",
        "last_discharge_consultation_symptoms_onset_date",
    ]

    ordering_fields = [
        "id",
        "name",
        "created_date",
        "modified_date",
        "review_time",
        "last_discharge_consultation__current_bed__bed__name",
        "date_declared_positive",
    ]

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        return qs.filter(
            id__in=PatientConsultation.objects.filter(
                discharge_date__isnull=False,
                facility__external_id=self.kwargs["facility_external_id"],
            ).values_list("patient_id")
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
    ).order_by("id")
    serializer_class = PatientSearchSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    pagination_class = PatientSearchSetPagination

    def get_queryset(self):
        if self.action != "list":
            return super().get_queryset()
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

        if "age" in search_fields:
            age = search_fields.pop("age")
            year_of_birth = timezone.now().year - age
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
        return super().list(request, *args, **kwargs)


class PatientNotesFilterSet(filters.FilterSet):
    thread = filters.ChoiceFilter(choices=PatientNoteThreadChoices.choices)
    consultation = filters.CharFilter(field_name="consultation__external_id")


class PatientNotesEditViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = PatientNotesEdit.objects.all().order_by("-edited_date")
    lookup_field = "external_id"
    serializer_class = PatientNotesEditSerializer

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
        .select_related(
            "facility", "patient", "created_by", "reply_to", "reply_to__created_by"
        )
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
