from django.contrib.postgres.fields import JSONField
from django.db import models
from multiselectfield import MultiSelectField

from care.facility.models import CATEGORY_CHOICES, PatientBaseModel
from care.facility.models.patient_base import (
    ADMIT_CHOICES,
    CURRENT_HEALTH_CHOICES,
    SYMPTOM_CHOICES,
)
from care.facility.models.patient_consultation import PatientConsultation
from care.users.models import User


class DailyRound(PatientBaseModel):
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, related_name="daily_rounds")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, default=0)
    spo2 = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, default=None)
    temperature_measured_at = models.DateTimeField(null=True, blank=True)
    physical_examination_info = models.TextField(null=True, blank=True)
    additional_symptoms = MultiSelectField(choices=SYMPTOM_CHOICES, default=1, null=True, blank=True)
    other_symptoms = models.TextField(default="", blank=True)
    patient_category = models.CharField(choices=CATEGORY_CHOICES, max_length=8, default=None, blank=True, null=True)
    current_health = models.IntegerField(default=0, choices=CURRENT_HEALTH_CHOICES, blank=True)
    recommend_discharge = models.BooleanField(default=False, verbose_name="Recommend Discharging Patient")
    other_details = models.TextField(null=True, blank=True)
    medication_given = JSONField(default=dict)  # To be Used Later on
    admitted_to = models.IntegerField(choices=ADMIT_CHOICES, default=None, null=True, blank=True)
    last_updated_by_telemedicine = models.BooleanField(default=False)
    created_by_telemedicine = models.BooleanField(default=False)

    @staticmethod
    def has_write_permission(request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return DailyRound.has_read_permission(request)

    @staticmethod
    def has_read_permission(request):
        consultation = PatientConsultation.objects.get(
            external_id=request.parser_context["kwargs"]["consultation_external_id"]
        )
        return request.user.is_superuser or (
            (request.user in consultation.patient.facility.users.all())
            or (request.user == consultation.assigned_to or request.user == consultation.patient.assigned_to)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (request.user.district == consultation.patient.facility.district)
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (request.user.state == consultation.patient.facility.state)
            )
        )

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or (self.consultation.patient.facility and request.user in self.consultation.patient.facility.users.all())
            or (self.consultation.assigned_to == request.user or request.user == self.consultation.patient.assigned_to)
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.district == self.consultation.patient.facility.district
                )
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (
                    self.consultation.patient.facility
                    and request.user.state == self.consultation.patient.facility.district
                )
            )
        )

    def has_object_write_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return self.has_object_read_permission(request)
