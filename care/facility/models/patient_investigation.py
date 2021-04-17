from django.db import models
from care.facility.models.base import BaseModel
from care.facility.models.patient_consultation import PatientConsultation
import enum


TestTypeChoices = [("Float", "Float"), ("String", "String")]


class PatientInvestigationGroup(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)


class PatientInvestigation(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)
    group = models.ManyToManyField(PatientInvestigationGroup)
    unit = models.TextField()
    ideal_value = models.TextField(blank=False, null=False)
    min_value = models.FloatField(blank=True, default=None, null=True)
    max_value = models.FloatField(blank=True, default=None, null=True)
    test_type = models.CharField(max_length=10, choices=TestTypeChoices, blank=False, null=True, default=None)


class InvestigationSession(BaseModel):
    session = models.UUIDField(db_index=True)


class InvestigationValue(BaseModel):
    test = models.ForeignKey(PatientInvestigation, on_delete=models.PROTECT, blank=False, null=False)
    group = models.ForeignKey(PatientInvestigationGroup, on_delete=models.PROTECT, blank=True, null=True)
    value = models.FloatField(blank=True, null=True, default=None)
    notes = models.TextField(blank=True, null=True, default=None)
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, blank=False, null=False)
    session_id = models.ForeignKey(InvestigationSession, on_delete=models.PROTECT, blank=False, null=False)
