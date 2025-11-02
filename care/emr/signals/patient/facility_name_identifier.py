"""
This signal is used to create a patient identifier with the same name as the patient
This allows workflows without strict Authz to function as needed
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.encounter import Encounter
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.signals.patient.base import BasePatientIdentifierConfig


class FacilityPatientNameIdentifierConfig(BasePatientIdentifierConfig):
    IDENTIFIER_SYSTEM = "system.care.ohc.network/patient-name"
    CACHED_CONFIG = {}
    DISPLAY = "Patient Name"
    RETRIEVE_WITH_YOB = False
    PARTIAL_SEARCH = True

    @classmethod
    def get_value(cls, patient):
        return patient.name


@receiver(post_save, sender=Encounter)
def update_facility_name_identifier_on_encounter_save(
    sender, instance, created, **kwargs
):
    if settings.MAINTAIN_FACILITY_PATIENT_NAME_IDENTIFIER:
        FacilityPatientNameIdentifierConfig.update_identifier(
            instance.patient, instance.facility
        )


@receiver(post_save, sender=TokenBooking)
def update_facility_name_identifier_on_token_booking_save(
    sender, instance, created, **kwargs
):
    if not instance.token_slot.resource.user:
        return
    if settings.MAINTAIN_FACILITY_PATIENT_NAME_IDENTIFIER:
        FacilityPatientNameIdentifierConfig.update_identifier(
            instance.patient, instance.token_slot.resource.facility
        )
