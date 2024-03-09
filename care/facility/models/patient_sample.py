from django.db import models
from django.utils.translation import gettext_lazy as _

from care.facility.models import FacilityBaseModel, PatientRegistration, reverse_choices
from care.users.models import User


#
# SAMPLE_TYPE_CHOICES = [
#     (0, "UNKNOWN"),
#     (1, "BA/ETA"),
#     (2, "TS/NPS/NS"),
#     (3, "Blood in EDTA"),
#     (4, "Acute Sera"),
#     (5, "Covalescent sera"),
#     (6, "Biopsy"),
#     (7, "AMR"),
#     (8, "Communicable Diseases"),
#     (9, "OTHER TYPE"),
# ]

class SampleTypeChoices(models.IntegerChoices):
    UNKNOWN = 0, _("Unknown")
    BA_ETA = 1, _("BA/ETA")
    TS_NPS_NS = 2, _("TS/NPS/NS")
    BLOOD_IN_EDTA = 3, _("Blood in EDTA")
    ACUTE_SERA = 4, _("Acute Sera")
    COVALESCENT_SERA = 5, _("Covalescent sera")
    BIOPSY = 6, _("Biopsy")
    AMR = 7, _("AMR")
    COMMUNICABLE_DISEASES = 8, _("Communicable Diseases")
    OTHER_TYPE = 9, _("Other Type")


class PatientSample(FacilityBaseModel):
    class SampleTestResultChoices(models.IntegerChoices):
        POSITIVE = 1, _("Positive")
        NEGATIVE = 2, _("Negative")
        AWAITING = 3, _("Awaiting")
        INVALID = 4, _("Invalid")

    # SAMPLE_TEST_RESULT_MAP = {"POSITIVE": 1, "NEGATIVE": 2, "AWAITING": 3, "INVALID": 4}
    # SAMPLE_TEST_RESULT_CHOICES = [(v, k) for k, v in SAMPLE_TEST_RESULT_MAP.items()]
    # REVERSE_SAMPLE_TEST_RESULT_CHOICES = reverse_choices(SAMPLE_TEST_RESULT_CHOICES)

    #
    # PATIENT_ICMR_CATEGORY = [
    #     (0, "Cat 0"),
    #     (10, "Cat 1"),
    #     (20, "Cat 2"),
    #     (30, "Cat 3"),
    #     (40, "Cat 4"),
    #     (50, "Cat 5a"),
    #     (60, "Cat 5b"),
    # ]

    class PatientICMRCategory(models.IntegerChoices):
        CAT_0 = 0, _("Category 0")
        CAT_1 = 10, _("Category 1")
        CAT_2 = 20, _("Category 2")
        CAT_3 = 30, _("Category 3")
        CAT_4 = 40, _("Category 4")
        CAT_5A = 50, _("Category 5a")
        CAT_5B = 60, _("Category 5b")

    # SAMPLE_TEST_FLOW_MAP = {
    #     "REQUEST_SUBMITTED": 1,
    #     "APPROVED": 2,
    #     "DENIED": 3,
    #     "SENT_TO_COLLECTON_CENTRE": 4,
    #     "RECEIVED_AND_FORWARED": 5,
    #     "RECEIVED_AT_LAB": 6,
    #     "COMPLETED": 7,
    # }
    # SAMPLE_TEST_FLOW_CHOICES = [(v, k) for k, v in SAMPLE_TEST_FLOW_MAP.items()]

    class SampleTestFlow(models.IntegerChoices):
        REQUEST_SUBMITTED = 1, _("Request Submitted")
        APPROVED = 2, _("Approved")
        DENIED = 3, _("Denied")
        SENT_TO_COLLECTION_CENTRE = 4, _("Sent to Collection Centre")
        RECEIVED_AND_FORWARDED = 5, _("Received and Forwarded")
        RECEIVED_AT_LAB = 6, _("Received at Lab")
        COMPLETED = 7, _("Completed")

    SAMPLE_FLOW_RULES = {
        # previous rule      # next valid rules
        "REQUEST_SUBMITTED": {
            "APPROVED",
            "DENIED",
        },
        "APPROVED": {
            "SENT_TO_COLLECTON_CENTRE",
            "RECEIVED_AND_FORWARED",
            "RECEIVED_AT_LAB",
            "COMPLETED",
        },
        "DENIED": {"REQUEST_SUBMITTED"},
        "SENT_TO_COLLECTON_CENTRE": {
            "RECEIVED_AND_FORWARED",
            "RECEIVED_AT_LAB",
            "COMPLETED",
        },
        "RECEIVED_AND_FORWARED": {"RECEIVED_AT_LAB", "COMPLETED"},
        "RECEIVED_AT_LAB": {"COMPLETED"},
        "COMPLETED": {"COMPLETED"},
    }

    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT)
    consultation = models.ForeignKey("PatientConsultation", on_delete=models.PROTECT)

    sample_type = models.IntegerField(choices=SampleTypeChoices.choices, default=SampleTypeChoices.UNKNOWN)
    sample_type_other = models.TextField(default="")

    has_sari = models.BooleanField(default=False)
    has_ari = models.BooleanField(default=False)

    doctor_name = models.CharField(max_length=255, default="NO DOCTOR SPECIFIED")
    diagnosis = models.TextField(default="")
    diff_diagnosis = models.TextField(default="")
    etiology_identified = models.TextField(default="")
    is_atypical_presentation = models.BooleanField(default=False)
    atypical_presentation = models.TextField(default="")
    is_unusual_course = models.BooleanField(default=False)

    icmr_category = models.IntegerField(choices=PatientICMRCategory.choices, default=PatientICMRCategory.CAT_0)

    icmr_label = models.CharField(max_length=200, default="")

    status = models.IntegerField(
        choices=SampleTestFlow.choices,
        default=SampleTestFlow.REQUEST_SUBMITTED,
    )
    result = models.IntegerField(
        choices=SampleTestResultChoices, default=SampleTestResultChoices.AWAITING
    )

    fast_track = models.TextField(default="")

    date_of_sample = models.DateTimeField(null=True, blank=True)
    date_of_result = models.DateTimeField(null=True, blank=True)

    testing_facility = models.ForeignKey(
        "Facility", on_delete=models.SET_NULL, null=True, blank=True
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="samples_created"
    )
    last_edited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="last_edited_by"
    )

    CSV_MAPPING = {
        "patient__name": "Patient Name",
        "patient__phone_number": "Patient Phone Number",
        "patient__age": "Patient Age",
        "testing_facility__name": "Testing Facility",
        "sample_type": "Type",
        "sample_type_other": "Other Type",
        "status": "Status",
        "result": "Result",
        "date_of_sample": "Date of Sample",
        "date_of_result": "Date of Result",
    }

    CSV_MAKE_PRETTY = {
        "sample_type": (lambda x: SampleTypeChoices(x).label if x in SampleTypeChoices.values else "-"),
        "status": (
            lambda x: PatientSample.SampleTestFlow(x) if x in PatientSample.SampleTestFlow.values else "-"
        ),
        "result": (
            lambda x: PatientSample.SampleTestResultChoices(x).label if x in PatientSample.SampleTestResultChoices.values else "-"
        ),
    }

    def save(self, *args, **kwargs) -> None:
        if self.testing_facility is None:
            self.testing_facility = self.patient.facility
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.patient.name} - {self.sample_type}"

    @property
    def flow(self):
        try:
            return self.flow_prefetched
        except AttributeError:
            return self.patientsampleflow_set.order_by("-created_date")

    @staticmethod
    def has_write_permission(request):
        if request.user.is_superuser:
            return True
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and request.user.user_type >= User.TYPE_VALUE_MAP["Nurse"]
        )

    @staticmethod
    def has_read_permission(request):
        return (
            request.user.is_superuser
            or request.user.user_type >= User.TYPE_VALUE_MAP["NurseReadOnly"]
        )

    @staticmethod
    def has_update_permission(request):
        return (
            request.user.is_superuser
            or request.user.user_type >= User.TYPE_VALUE_MAP["Doctor"]
        )

    def has_object_read_permission(self, request):
        if request.user.user_type < User.TYPE_VALUE_MAP["NurseReadOnly"]:
            return False

        if self.testing_facility:
            test_facility = request.user in self.testing_facility.users.all()

        return (
            request.user.is_superuser
            or request.user == self.consultation.facility.created_by
            or (
                request.user.district == self.consultation.facility.district
                and request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
            )
            or (
                request.user.state == self.consultation.facility.state
                and request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
            )
            or request.user in self.patient.facility.users.all()
            or test_facility
        )

    def has_object_update_permission(self, request):
        return (
            request.user.user_type not in User.READ_ONLY_TYPES
            and self.has_object_read_permission(request)
        )

    def has_object_destroy_permission(self, request):
        return request.user.is_superuser


class PatientSampleFlow(FacilityBaseModel):
    patient_sample = models.ForeignKey(PatientSample, on_delete=models.PROTECT)
    status = models.IntegerField(choices=PatientSample.SampleTestFlow.choices)
    notes = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
