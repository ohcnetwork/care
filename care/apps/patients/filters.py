from django_filters import rest_framework as filters

from apps.commons import constants as common_constants
from apps.patients import models as patients_models
from apps.patients import constants as patient_constants


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
    gender = filters.ChoiceFilter(
        field_name="gender", choices=common_constants.GENDER_CHOICES
    )
    years = filters.CharFilter(field_name="year")
    months = filters.CharFilter(field_name="month")
    contact = filters.CharFilter(field_name="phone_number", lookup_expr="istartswith")
    address = filters.CharFilter(field_name="address", lookup_expr="istartswith")
    district = filters.CharFilter(field_name="district")
    cluster = filters.CharFilter(field_name="cluster_group")
    covid_status = filters.CharFilter(field_name="covid_status")
    patient_status = filters.ChoiceFilter(
        field_name="patient_status", choices=patient_constants.PATIENT_STATUS_CHOICES
    )
    clinical_status = filters.CharFilter(field_name="clinical_status")
    clinical_status_updated_at = filters.DateFromToRangeFilter(
        field_name="clinical_status_updated_at"
    )
    portea_called_at = filters.DateFromToRangeFilter(field_name="portea_called_at")
    portea_able_to_connect = filters.BooleanFilter(field_name="portea_able_to_connect")
    facility_name = filters.CharFilter(field_name="facility__name")
    facility_district = filters.CharFilter(field_name="facility__district")
    facility_type = filters.CharFilter(field_name="facility__facility_type")
    facility_owned_by = filters.CharFilter(field_name="facility__owned_by")
    current_facility_status = filters.CharFilter(
        field_name="current_facility__patient_status__name"
    )

    class Meta:
        model = patients_models.Patient
        fields = (
            "name",
            "icmr",
            "govt",
            "facility",
            "gender",
            "years",
            "months",
            "contact",
            "address",
            "district",
            "cluster",
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
            "current_facility_status",
        )
