from django.db.models import Q
from django_filters import rest_framework as filters

from apps.commons import constants as common_constants
from apps.patients import models as patients_models, constants as patient_constants
from apps.accounts import models as accounts_models


class PatientTimelineFilter(filters.FilterSet):
    description = filters.CharFilter(
        field_name="description", lookup_expr="istartswith"
    )

    class Meta:
        model = patients_models.PatientTimeLine
        fields = ("date", "description")


class PatientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="istartswith")
    icmr = filters.CharFilter(field_name="icmr_id", lookup_expr="istartswith")
    govt = filters.CharFilter(field_name="govt_id", lookup_expr="istartswith")
    facility = filters.CharFilter(field_name="facility")
    gender = filters.MultipleChoiceFilter(
        field_name="gender", choices=common_constants.GENDER_CHOICES
    )
    year = filters.RangeFilter(field_name="year", lookup_expr="range")
    month = filters.RangeFilter(field_name="month", lookup_expr="range")
    contact = filters.CharFilter(field_name="phone_number", lookup_expr="istartswith")
    address = filters.CharFilter(field_name="address", lookup_expr="istartswith")
    district = filters.MultipleChoiceFilter(
        field_name="district",
        choices=accounts_models.District.objects.all().values_list("id", "name"),
    )
    cluster_group = filters.MultipleChoiceFilter(
        field_name="cluster_group",
        choices=patients_models.PatientGroup.objects.all().values_list("id", "name"),
    )
    covid_status = filters.MultipleChoiceFilter(
        field_name="covid_status",
        choices=patients_models.CovidStatus.objects.all().values_list("id", "name"),
    )
    clinical_status = filters.MultipleChoiceFilter(
        field_name="clinical_status",
        choices=patients_models.ClinicalStatus.objects.all().values_list("id", "name"),
    )
    clinical_status_updated_at = filters.DateFromToRangeFilter(
        field_name="clinical_status_updated_at"
    )
    portea_called_at = filters.DateFromToRangeFilter(field_name="portea_called_at")
    portea_able_to_connect = filters.BooleanFilter(field_name="portea_able_to_connect")
    facility_name = filters.MultipleChoiceFilter(
        field_name="facility",
        choices=patients_models.Facility.objects.all().values_list("id", "name"),
    )
    facility_district = filters.CharFilter(field_name="facility__district")
    facility_type = filters.CharFilter(field_name="facility__facility_type")
    facility_owned_by = filters.CharFilter(field_name="facility__owned_by")
    patient_status = filters.MultipleChoiceFilter(
        field_name="patient_status",
        # method="filter_patient_status",
        choices=patient_constants.PATIENT_STATUS_CHOICES,
    )

    def filter_patient_status(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(current_facility__patient_status__name=value)
                | Q(patient_status=value)
            )
        return queryset

    class Meta:
        model = patients_models.Patient
        fields = (
            "name",
            "icmr",
            "govt",
            "facility",
            "gender",
            "year",
            "month",
            "contact",
            "address",
            "district",
            "cluster_group",
            "covid_status",
            "patient_status",
            "clinical_status",
            "clinical_status_updated_at",
            "portea_called_at",
            "portea_able_to_connect",
            "facility_name",
            "facility_district",
            "facility_type",
            "facility_owned_by",
        )


class PatientTransferFilter(filters.FilterSet):
    gender = filters.ChoiceFilter(
        field_name="from_patient_facility__patient__gender",
        choices=common_constants.GENDER_CHOICES,
    )
    years = filters.CharFilter(field_name="from_patient_facility__patient__year")
    months = filters.CharFilter(field_name="from_patient_facility__patient__month")
    from_facility = filters.CharFilter(field_name="from_patient_facility_id")
    to_facility = filters.CharFilter(field_name="to_facility_id")
    requested_at = filters.DateTimeFromToRangeFilter(field_name="created_at")
    status_updated_at = filters.DateTimeFromToRangeFilter(
        field_name="status_updated_at"
    )
    status = filters.ChoiceFilter(
        field_name="status", choices=patient_constants.TRANSFER_STATUS_CHOICES
    )

    class Meta:
        model = patients_models.PatientTransfer
        fields = (
            "gender",
            "years",
            "months",
            "from_facility",
            "to_facility",
            "requested_at",
            "status_updated_at",
            "status",
        )
