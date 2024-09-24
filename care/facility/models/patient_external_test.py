from django.db import models

from care.facility.models import FacilityBaseModel, pretty_boolean
from care.users.models import District, LocalBody, Ward


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
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, null=True, blank=True)
    local_body = models.ForeignKey(
        LocalBody, on_delete=models.PROTECT, null=False, blank=False
    )
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, null=False, blank=False
    )
    source = models.CharField(max_length=255, blank=True, null=True)
    patient_category = models.CharField(max_length=255, blank=True, null=True)
    lab_name = models.CharField(max_length=255)
    test_type = models.CharField(max_length=255)
    sample_type = models.CharField(max_length=255)
    result = models.CharField(max_length=255)
    sample_collection_date = models.DateField(blank=True, null=True)
    result_date = models.DateField(blank=True, null=True)
    patient_created = models.BooleanField(default=False)

    CSV_MAPPING = {
        "id": "Care External Result ID",
        "name": "Patient Name",
        "age": "Age",
        "age_in": "Age In",
        "result": "Final Result",
        "srf_id": "SRF-ID",
        "gender": "Gender",
        "address": "Patient Address",
        "district__name": "District",
        "local_body__name": "LSGD",
        "ward__name": "Ward Name",
        "ward__number": "Ward Number",
        "mobile_number": "Contact Number",
        "is_repeat": "Is Repeat",
        "patient_status": "Patient Status",
        "sample_type": "Sample Type",
        "test_type": "Testing Kit Used",
        "sample_collection_date": "Sample Collection Date",
        "result_date": "Result Date",
        "lab_name": "LabName",
        "source": "Source",
        "patient_category": "Patient Category",
    }

    CSV_MAKE_PRETTY = {"is_repeat": pretty_boolean}

    HEADER_CSV_MAPPING = {
        "srf_id": "SRF-ID",
        "name": "Patient Name",
        "age": "Age",
        "age_in": "Age In",
        "gender": "Gender",
        "address": "Patient Address",
        "mobile_number": "Contact Number",
        "is_repeat": "Is Repeat",
        "patient_status": "Patient Status",
        "ward": "Ward",
        "district": "District",
        "result_date": "Result Date",
        "local_body": "LSGD",
        "local_body_type": "LSGD Type",
        "lab_name": "LabName",
        "test_type": "Testing Kit Used",
        "sample_type": "Sample Type",
        "result": "Final Result",
        "sample_collection_date": "Sample Collection Date",
        "source": "Source",
    }

    def __str__(self):
        return self.name + " on " + self.created_date.strftime("%d-%m-%Y")
