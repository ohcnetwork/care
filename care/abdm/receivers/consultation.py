from django.db.models.signals import post_save
from django.dispatch import receiver

from care.abdm.utils.api_call import AbdmGateway
from care.facility.models import PatientConsultation


@receiver(post_save, sender=PatientConsultation)
def create_care_context(sender, instance, created, **kwargs):
    patient = instance.patient

    if created and hasattr(patient, "abha_number") and patient.abha_number is not None:
        abha_number = patient.abha_number

        try:
            AbdmGateway().fetch_modes(
                {
                    "healthId": abha_number.abha_number,
                    "name": abha_number.name,
                    "gender": abha_number.gender,
                    "dateOfBirth": str(abha_number.date_of_birth),
                    "consultationId": instance.external_id,
                    "purpose": "LINK",
                }
            )
        except Exception:
            pass
