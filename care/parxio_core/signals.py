from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequestPrescription
from care.parxio_core.services import ABDMService


@receiver(post_save, sender=Encounter)
def encounter_saved_sync_abdm(sender, instance, **kwargs):
    ABDMService.sync_incentive(instance)


@receiver(post_save, sender=MedicationRequestPrescription)
def prescription_saved_sync_abdm(sender, instance, **kwargs):
    ABDMService.sync_incentive(instance.encounter, instance)
