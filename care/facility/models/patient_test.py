from django.db import models
from care.facility.models.base import BaseModel
from care.facility.models.patient_consultation import PatientConsultation
import enum


TestTypeChoices = [("Float", "Float"), ("String", "String")]


class PatientTestGroup(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)


class PatientTest(BaseModel):
    name = models.CharField(max_length=500, blank=False, null=False)
    group = models.ManyToManyField(PatientTestGroup)
    unit = models.TextField()
    ideal_value = models.TextField(blank=False, null=False)
    min_value = models.FloatField(blank=True, default=None, null=True)
    max_value = models.FloatField(blank=True, default=None, null=True)
    test_type = models.CharField(max_length=10, choices=TestTypeChoices, blank=False, null=True, default=None)


class TestSession(BaseModel):
    session = models.UUIDField(db_index=True)


class TestValue(BaseModel):
    test = models.ForeignKey(PatientTest, on_delete=models.PROTECT, blank=False, null=False)
    group = models.ForeignKey(PatientTestGroup, on_delete=models.PROTECT, blank=True, null=True)
    value = models.FloatField(blank=True, null=True, default=None)
    notes = models.TextField(blank=True, null=True, default=None)
    consultation = models.ForeignKey(PatientConsultation, on_delete=models.PROTECT, blank=False, null=False)
    session_id = models.ForeignKey(TestSession, on_delete=models.PROTECT, blank=False, null=False)
