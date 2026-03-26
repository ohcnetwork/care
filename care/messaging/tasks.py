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
    # Simply listing active meds for all verified profiles for demo
    profiles = WhatsAppProfile.objects.filter(is_verified=True, can_receive_ppi=True)
    provider = WhatsAppProvider()
    
    for profile in profiles:
        active_meds = MedicationRequest.objects.filter(
            patient__user=profile.user, status="active"
        )
        if active_meds.exists():
            message = "🔔 *Reminder: You have active medications!*"
            for med in active_meds:
                message += f"\n- {med.medication_display}" # Should use spec if possible
            
            try:
                provider.send_message(profile.whatsapp_id, message)
            except Exception as e:
                logger.error(f"Failed to send reminder to {profile.whatsapp_id}: {e}")

@shared_task
def send_proactive_notification(whatsapp_id, message):
    """
    Task to send a single proactive notification.
    """
    provider = WhatsAppProvider()
    provider.send_message(whatsapp_id, message)
