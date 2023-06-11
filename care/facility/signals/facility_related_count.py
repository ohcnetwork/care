from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from care.facility.models.bed import Bed
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientRegistration
from care.utils.models.aggregators import update_related_count_for_single_object


def update_patient_count(facility: Facility):
    update_related_count_for_single_object(
        facility,
        {
            "patient_count": (
                "patientregistration_set",
                Q(
                    is_active=True,
                    deleted=False,
                ),
            )
        },
    )


def update_bed_count(facility: Facility):
    update_related_count_for_single_object(
        facility,
        {
            "bed_count": ("bed_set", Q(is_active=True, deleted=False)),
        },
    )


@receiver(post_save, sender=PatientRegistration)
def patient_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
    if raw:
        return
    if (
        created or (update_fields is not None and "is_active" in update_fields)
    ) and instance.facility is not None:
        update_patient_count(instance.facility)


@receiver(post_delete, sender=PatientRegistration)
def patient_post_delete(sender, instance, **kwargs):
    if instance.facility is not None:
        update_patient_count(instance.facility)


@receiver(post_save, sender=Bed)
def bed_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
    if created:
        update_bed_count(instance.facility)


@receiver(post_delete, sender=Bed)
def bed_post_delete(sender, instance, **kwargs):
    update_bed_count(instance.facility)
