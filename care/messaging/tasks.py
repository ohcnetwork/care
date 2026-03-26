import logging
from collections import defaultdict
from celery import shared_task
from care.messaging.models import WhatsAppProfile
from care.messaging.providers.whatsapp import WhatsAppProvider
from care.emr.models.medication_request import MedicationRequest

logger = logging.getLogger(__name__)


@shared_task
def send_whatsapp_medication_reminders():
    """
    Efficient periodic task to send medication reminders to linked WhatsApp users.
    Uses bulk queries to avoid N+1 performance issues.
    """
    profiles = WhatsAppProfile.objects.filter(
        is_verified=True, can_receive_ppi=True
    ).select_related("user")
    
    if not profiles.exists():
        return

    # Map user IDs to profiles
    user_to_profile = {p.user.id: p for p in profiles}
    
    # Bulk fetch all active medications for these users
    active_meds_all = MedicationRequest.objects.filter(
        patient__patientuser__user_id__in=user_to_profile.keys(),
        status="active"
    ).values("patient__patientuser__user_id", "medication")

    # Group medications by user
    user_meds = defaultdict(list)
    for med in active_meds_all:
        user_id = med["patient__patientuser__user_id"]
        med_name = med["medication"].get("display", "Unknown medication") if med["medication"] else "Unknown medication"
        user_meds[user_id].append(med_name)

    provider = WhatsAppProvider()

    for user_id, med_list in user_meds.items():
        profile = user_to_profile[user_id]
        message = "🔔 *Reminder: You have active medications!*"
        for med_name in med_list:
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
