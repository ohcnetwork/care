from django.db import models

from care.facility.models import FacilityBaseModel, PatientRegistration
from care.users.models import User, Ward, LocalBody, District


class PatientExternalTest(FacilityBaseModel):
    srf_id = models.CharField(max_length=255)
    name = models.CharField(max_length=1000)
    age = models.IntegerField()
    age_in = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    address = models.TextField()
    mobile_number = models.CharField(max_length=15)
    is_repeat = models.BooleanField()
    patient_status = models.CharField(max_length=15)
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, null=False, blank=False)
    local_body = models.ForeignKey(LocalBody, on_delete=models.PROTECT, null=False, blank=False)
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=False, blank=False)
    lab_name = models.CharField(max_length=255)
    test_type = models.CharField(max_length=255)
    sample_type = models.CharField(max_length=255)
    result = models.CharField(max_length=255)
    sample_collection_date = models.DateTimeField()
    result_date = models.DateTimeField()

    header_csv_mapping = {
        "srf_id": "SRF-ID",
    }
