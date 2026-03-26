import logging
from celery import shared_task
from care.messaging.models import WhatsAppProfile
from care.messaging.providers.whatsapp import WhatsAppProvider
from care.emr.models.medication_request import MedicationRequest

logger = logging.getLogger(__name__)


@shared_task
def send_whatsapp_medication_reminders():
    """
    Periodic task to send medication reminders to linked WhatsApp users.
    """
    # Use select_related to avoid N+1 queries when accessing profile.user
    profiles = WhatsAppProfile.objects.filter(
        is_verified=True, can_receive_ppi=True
    ).select_related("user")
    provider = WhatsAppProvider()

    for profile in profiles:
        # Corrected ORM lookup: patient -> patientuser -> user
        active_meds = MedicationRequest.objects.filter(
            patient__patientuser__user=profile.user, status="active"
        )
        if active_meds.exists():
            message = "🔔 *Reminder: You have active medications!*"
            for med in active_meds:
                # Corrected attribute access: medication is a JSONField
                med_name = (
                    med.medication.get("display", "Unknown medication")
                    if med.medication
                    else "Unknown medication"
                )
                message += f"\n- {med_name}"

            try:
                provider.send_message(profile.whatsapp_id, message)
            except Exception as e:
                logger.error(f"Failed to send reminder to {profile.whatsapp_id}: {e}")


@shared_task
def send_proactive_notification(whatsapp_id, message):
    """
    Task to send a single proactive notification after verifying security flags.
    """
    # Security Check: Respect can_receive_ppi flag even for proactive tasks
    profile = WhatsAppProfile.objects.filter(
        whatsapp_id=whatsapp_id, can_receive_ppi=True
    ).first()
    if not profile:
        logger.warning(
            f"Blocked proactive notification to {whatsapp_id}: No verified profile or PII permission."
        )
        return

    provider = WhatsAppProvider()
    try:
        provider.send_message(whatsapp_id, message)
    except Exception as e:
        logger.error(f"Failed to send proactive notification to {whatsapp_id}: {e}")
