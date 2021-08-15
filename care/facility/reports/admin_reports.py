import enum
from datetime import time, timedelta

from django.utils.timezone import localtime, now

from care.facility.models import base
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_base import CATEGORY_CHOICES
from care.facility.models.shifting import SHIFTING_STATUS_CHOICES, ShiftingRequest
from care.users.models import User


class InvalidModeException(Exception):
    pass


class AdminReportsMode(enum.Enum):
    STATE = 1
    DISTRICT = 2


class AdminReports:

    mode = None
    filter_field = ""
    unique_object_ids = []
    start_date = None
    end_date = None

    def fetch_unique_districts(self) -> None:
        self.unique_object_ids = list(User.objects.all().values_list("district_id", flat=True).distinct())

    def fetch_unique_states(self) -> None:
        self.unique_object_ids = list(User.objects.all().values_list("state_id", flat=True).distinct())

    def __init__(self, mode) -> None:
        if mode == AdminReportsMode.DISTRICT:
            self.filter_field = "district_id"
            self.fetch_unique_districts()
        elif mode == AdminReportsMode.STATE:
            self.filter_field = "state_id"
            self.fetch_unique_states()
        else:
            raise InvalidModeException
        self.start_date = (localtime(now()) - timedelta(days=0)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_date = self.start_date + timedelta(days=1)

    # Summary Functions

    def calculate_patient_summary(self, base_filters):
        return_dict = {}
        base_queryset = PatientRegistration.objects.filter(**base_filters)
        return_dict["current_active"] = base_queryset.filter(is_active=True).count()
        return_dict["created_today"] = base_queryset.filter(
            is_active=True, created_date__gte=self.start_date, created_date__lte=self.end_date
        ).count()
        return_dict["discharged_today"] = base_queryset.filter(
            is_active=False,
            last_consultation__discharge_date__gte=self.start_date,
            last_consultation__discharge_date__lt=self.end_date,
        ).count()
        return return_dict

    def caluclate_patient_age_summary(self, base_filters):
        return_dict = {}
        base_queryset = PatientRegistration.objects.filter(**base_filters)
        age_brakets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 120)]
        for index, braket in enumerate(age_brakets):
            return_dict[index] = base_queryset.filter(
                is_active=True,
                created_date__gte=self.start_date,
                created_date__lte=self.end_date,
                age__gte=braket[0],
                age__lt=braket[1],
            ).count()
        return return_dict

    def caluclate_patient_category_summary(self, base_filters):
        return_dict = {}
        base_queryset = PatientRegistration.objects.filter(**base_filters)
        for category in CATEGORY_CHOICES:
            return_dict[category[1]] = base_queryset.filter(
                is_active=True,
                created_date__gte=self.start_date,
                created_date__lte=self.end_date,
                last_consultation__category=category[0],
            ).count()
        return return_dict

    def calculate_shifting_summary(self, base_filters):
        return_dict = {}
        base_queryset = ShiftingRequest.objects.filter(**base_filters)
        today_queryset = base_queryset.filter(created_date__gte=self.start_date, created_date__lte=self.end_date)
        return_dict["total_up"] = today_queryset.filter(is_up_shift=True).count()
        return_dict["total_down"] = today_queryset.filter(is_up_shift=False).count()
        return return_dict

    def calculate_shifting_status_summary(self, base_filters):
        return_dict = {}
        base_queryset = ShiftingRequest.objects.filter(**base_filters)
        today_queryset = base_queryset.filter(created_date__gte=self.start_date, created_date__lte=self.end_date)
        for status in SHIFTING_STATUS_CHOICES:
            total = today_queryset.filter(status=status[0]).count()
            emergency = today_queryset.filter(status=status[0], emergency=True).count()
            return_dict["_".join(status[1].split(" "))] = {total: total, emergency: emergency}
        return return_dict

    def genearte_report_data(self, object_id):
        final_data = {}
        base_filters = {self.filter_field: object_id}
        shifting_base_filter = {"patient__" + self.filter_field: object_id}
        final_data["patients_summary"] = self.calculate_patient_summary(base_filters)
        final_data["patients_age"] = self.caluclate_patient_age_summary(base_filters)
        final_data["patients_category"] = self.caluclate_patient_category_summary(base_filters)
        final_data["shifting_summary"] = self.calculate_shifting_summary(shifting_base_filter)
        final_data["shifting_status"] = self.calculate_shifting_status_summary(shifting_base_filter)
        return final_data

    def generate_reports(self):
        for object_id in self.unique_object_ids:
            data = self.genearte_report_data(object_id)
            print(data)
            return
