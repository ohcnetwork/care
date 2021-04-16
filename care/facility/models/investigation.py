from django.db import models
from django.contrib.postgres.fields import JSONField
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.base import BaseModel


class Investigation(BaseModel):
    consultation = models.OneToOneField(
        PatientConsultation,
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )
    investigation_data = JSONField(default=dict, null=False)

# p = PatientConsultation(facility_id = 1, patient_id= 4)
# i = Investigation(consultation_id = 1, investigation_data={"platelets" : 1000})
