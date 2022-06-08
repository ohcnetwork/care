from django.db import models
from care.utils.models.base import BaseModel
from care.facility.models.patient_consultation import PatientConsultation
from uuid import uuid4
from care.users.models import User


TestTypeChoices = [("Float", "Float"), ("String", "String"), ("Choice", "Choice")]


class PatientInvestigationGroup(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)

    def __str__(self) -> str:
        return self.name


class PatientInvestigation(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)
    groups = models.ManyToManyField(PatientInvestigationGroup)
    unit = models.TextField(null=True, blank=True)
    ideal_value = models.TextField(blank=True, null=True)
    min_value = models.FloatField(blank=True, default=None, null=True)
    max_value = models.FloatField(blank=True, default=None, null=True)
    investigation_type = models.CharField(max_length=10, choices=TestTypeChoices, blank=False, null=True, default=None)
    choices = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name + " in " + self.unit + " as " + self.investigation_type


class InvestigationSession(BaseModel):
    external_id = models.UUIDField(default=uuid4, unique=True, db_index=True)  # session_id
    created_by = models.ForeignKey(User, null=False, blank=False, on_delete=models.PROTECT)

    class Meta:
        indexes = [
            models.Index(fields=["-created_date",]),
        ]


class InvestigationValue(BaseModel):
    investigation = models.ForeignKey(PatientInvestigation, on_delete=models.PROTECT, blank=False, null=False)
    group = models.ForeignKey(PatientInvestigationGroup, on_delete=models.PROTECT, blank=True, null=True)
    value = models.FloatField(blank=True, null=True, default=None)
    notes = models.TextField(blank=True, null=True, default=None)
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, blank=False, null=False)
    session = models.ForeignKey(InvestigationSession, on_delete=models.PROTECT, blank=False, null=False)
