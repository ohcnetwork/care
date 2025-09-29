"""
This signal is used to create a patient identifier with the same name as the patient
This allows workflows without strict Authz to function as needed
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.patient import Patient
from care.emr.signals.patient.base import BasePatientIdentifierConfig


class PhoneNumberIdentifierConfig(BasePatientIdentifierConfig):
    IDENTIFIER_SYSTEM = "system.care.ohc.network/patient-phone-number"
    CACHED_CONFIG = {}
    DISPLAY = "Patient Phone Number"
    RETRIEVE_WITH_YOB = True
    PARTIAL_SEARCH = False

    @classmethod
    def get_value(cls, patient):
        return patient.phone_number


@receiver(post_save, sender=Patient)
def update_phone_number_identifier(sender, instance, created, **kwargs):
    if settings.MAINTAIN_PATIENT_PHONE_NUMBER_IDENTIFIER:
        PhoneNumberIdentifierConfig.update_identifier(instance)
