from django.db import models

from care.facility.models import FacilityBaseModel, PatientRegistration
from care.users.models import User


class PatientSample(FacilityBaseModel):
    SAMPLE_TEST_RESULT_MAP = {"POSITIVE": 1, "NEGATIVE": 2, "AWAITING": 3, "INVALID": 4}
    SAMPLE_TEST_RESULT_CHOICES = [(v, k) for k, v in SAMPLE_TEST_RESULT_MAP.items()]

    SAMPLE_TEST_FLOW_MAP = {
        "REQUEST_SUBMITTED": 1,
        "APPROVED": 2,
        "DENIED": 3,
        "SENT_TO_COLLECTON_CENTRE": 4,
        "RECEIVED_AND_FORWARED": 5,
        "RECEIVED_AT_LAB": 6,
        "COMPLETED": 7,
    }
    SAMPLE_TEST_FLOW_CHOICES = [(v, k) for k, v in SAMPLE_TEST_FLOW_MAP.items()]
    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT)
    consultation = models.ForeignKey("PatientConsultation", on_delete=models.PROTECT)

    status = models.IntegerField(choices=SAMPLE_TEST_FLOW_CHOICES, default=SAMPLE_TEST_FLOW_MAP["REQUEST_SUBMITTED"])
    result = models.IntegerField(choices=SAMPLE_TEST_RESULT_CHOICES, default=SAMPLE_TEST_RESULT_MAP["AWAITING"])

    date_of_sample = models.DateTimeField(null=True, blank=True)
    date_of_result = models.DateTimeField(null=True, blank=True)

    @property
    def flow(self):
        try:
            return self.flow_prefetched
        except AttributeError:
            return self.patientsampleflow_set.order_by("-created_date")

    @staticmethod
    def has_write_permission(request):
        return request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["Staff"]

    @staticmethod
    def has_read_permission(request):
        return True

    def has_object_read_permission(self, request):
        return True

    def has_object_update_permission(self, request):
        return request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]

    def has_object_destroy_permission(self, request):
        return request.user.is_superuser or request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]


class PatientSampleFlow(FacilityBaseModel):
    patient_sample = models.ForeignKey(PatientSample, on_delete=models.PROTECT)
    status = models.IntegerField(choices=PatientSample.SAMPLE_TEST_FLOW_CHOICES)
    notes = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
