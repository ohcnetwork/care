import enum
import time
from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.timezone import localtime, make_aware, now
from hardcopy import bytestring_to_pdf

from care.facility.models import base
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_base import CATEGORY_CHOICES
from care.facility.models.shifting import SHIFTING_STATUS_CHOICES, ShiftingRequest
from care.users.models import District, State, User

from django.conf import settings


class InvalidModeException(Exception):
    pass


class AdminReportsMode(enum.Enum):
    STATE = "State"
    DISTRICT = "District"


class AdminReports:

    mode = None
    filter_field = ""
    unique_object_ids = []
    start_date = None
    end_date = None

    def fetch_unique_districts(self) -> None:
        self.unique_object_ids = list(
            User.objects.filter(user_type=User.TYPE_VALUE_MAP["DistrictAdmin"], district__isnull=False)
            .values_list("district_id", flat=True)
            .distinct()
        )

    def fetch_unique_states(self) -> None:
        self.unique_object_ids = list(
            User.objects.filter(user_type=User.TYPE_VALUE_MAP["StateAdmin"], state__isnull=False)
            .values_list("state_id", flat=True)
            .distinct()
        )

    def __init__(self, mode) -> None:
        self.mode = mode
        if mode == AdminReportsMode.DISTRICT:
            self.filter_field = "district_id"
            self.fetch_unique_districts()
        elif mode == AdminReportsMode.STATE:
            self.filter_field = "state_id"
            self.fetch_unique_states()
        else:
            raise InvalidModeException
        self.start_date = (localtime(now()) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_date = self.start_date + timedelta(days=1)

    def get_object_name(self, object_id):
        if self.mode == AdminReportsMode.STATE:
            return State.objects.get(id=object_id).name
        elif self.mode == AdminReportsMode.DISTRICT:
            return District.objects.get(id=object_id).name

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
        return_list = []
        base_queryset = PatientRegistration.objects.filter(**base_filters)
        age_brakets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 120)]
        for braket in age_brakets:
            count = base_queryset.filter(
                is_active=True,
                created_date__gte=self.start_date,
                created_date__lte=self.end_date,
                age__gte=braket[0],
                age__lt=braket[1],
            ).count()
            return_list.append({"total_count": count, "title": f"{braket[0]}-{braket[1]}"})
        return return_list

    def caluclate_patient_category_summary(self, base_filters):
        return_list = []
        base_queryset = PatientRegistration.objects.filter(**base_filters)
        for category in CATEGORY_CHOICES:
            count = base_queryset.filter(
                is_active=True,
                created_date__gte=self.start_date,
                created_date__lte=self.end_date,
                last_consultation__category=category[0],
            ).count()
            return_list.append({"total_count": count, "title": category[1]})
        return return_list

    def calculate_shifting_summary(self, base_filters):
        return_dict = {}
        base_queryset = ShiftingRequest.objects.filter(**base_filters)
        today_queryset = base_queryset.filter(created_date__gte=self.start_date, created_date__lte=self.end_date)
        return_dict["total_up"] = today_queryset.filter(is_up_shift=True).count()
        return_dict["total_down"] = today_queryset.filter(is_up_shift=False).count()
        return_dict["total_count"] = return_dict["total_up"] + return_dict["total_down"]
        return return_dict

    def calculate_shifting_status_summary(self, base_filters):
        return_list = []
        base_queryset = ShiftingRequest.objects.filter(**base_filters)
        today_queryset = base_queryset.filter(created_date__gte=self.start_date, created_date__lte=self.end_date)
        for status in SHIFTING_STATUS_CHOICES:
            total = today_queryset.filter(status=status[0]).count()
            emergency = today_queryset.filter(status=status[0], emergency=True).count()
            return_list.append({"total_count": total, "emergency_count": emergency, "status": status[1]})
        return return_list

    def generate_report_data(self, object_id):
        final_data = {}
        base_filters = {self.filter_field: object_id}
        shifting_base_filter = {"patient__" + self.filter_field: object_id}
        final_data["patients_summary"] = self.calculate_patient_summary(base_filters)
        final_data["patients_age"] = self.caluclate_patient_age_summary(base_filters)
        final_data["patients_categories"] = self.caluclate_patient_category_summary(base_filters)
        final_data["shifting_summary"] = self.calculate_shifting_summary(shifting_base_filter)
        final_data["shifting_status"] = self.calculate_shifting_status_summary(shifting_base_filter)
        return final_data

    def generate_reports(self):
        for object_id in self.unique_object_ids:
            data = self.generate_report_data(object_id)
            data["object_type"] = self.mode.value
            object_name = self.get_object_name(object_id)
            data["object_name"] = object_name
            data["current_date"] = str(self.start_date.date())
            html_string = render_to_string("reports/daily_report.html", data)
            file_name = str(int(round(time.time() * 1000))) + str(object_id) + ".pdf"
            bytestring_to_pdf(
                html_string.encode(),
                default_storage.open(file_name, "w+"),
                **{
                    "no-margins": None,
                    "disable-gpu": None,
                    "disable-dev-shm-usage": False,
                    "window-size": "2480,3508",
                },
            )
            self.send_reports(object_name, {self.filter_field: object_id}, file_name)
            default_storage.delete(file_name)

    def send_report(self, object_name, file_name, user):
        if not user.email:
            return
        file = default_storage.open(file_name, "rb")
        msg = EmailMessage(
            f"Care Summary : {self.mode.value} {object_name} : {self.start_date.date()}",
            "Please find the attached report",
            settings.DEFAULT_FROM_EMAIL,
            (user.email,),
        )
        msg.content_subtype = "html"
        msg.attach(f"{self.mode.value}Report.pdf", file.read(), "application/pdf")
        msg.send()

    def send_reports(self, object_name, base_filters, file_name):
        users = User.objects.all()
        if self.mode == AdminReportsMode.STATE:
            users = users.filter(user_type=User.TYPE_VALUE_MAP["StateAdmin"], **base_filters)
        elif self.mode == AdminReportsMode.DISTRICT:
            users = users.filter(user_type=User.TYPE_VALUE_MAP["DistrictAdmin"], **base_filters)
        for user in users:
            self.send_report(object_name, file_name, user)
