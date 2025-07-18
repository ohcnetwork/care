from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

from .models import (
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppCommand,
    WhatsAppNotification
)
from care.emr.models.patient import Patient
from care.utils.notification_handler import NotificationGenerator

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WhatsAppSession)
def handle_session_created(sender, instance, created, **kwargs):
    """Handle WhatsApp session creation and updates"""
    if created:
        logger.info(f"New WhatsApp session created for {instance.phone_number}")
        
        # Cache session for quick lookup
        cache_key = f"whatsapp_session:{instance.phone_number}"
        cache.set(cache_key, instance.id, timeout=86400)  # 24 hours
    
    # Update last activity cache
    if instance.is_authenticated:
        activity_key = f"whatsapp_activity:{instance.phone_number}"
        cache.set(activity_key, timezone.now().isoformat(), timeout=86400)


@receiver(pre_delete, sender=WhatsAppSession)
def handle_session_deleted(sender, instance, **kwargs):
    """Clean up cache when session is deleted"""
    cache_key = f"whatsapp_session:{instance.phone_number}"
    cache.delete(cache_key)
    
    activity_key = f"whatsapp_activity:{instance.phone_number}"
    cache.delete(activity_key)
    
    logger.info(f"WhatsApp session deleted for {instance.phone_number}")


@receiver(post_save, sender=WhatsAppMessage)
def handle_message_logged(sender, instance, created, **kwargs):
    """Handle message logging and processing"""
    if created and instance.direction == 'incoming':
        logger.info(
            f"New incoming WhatsApp message from {instance.phone_number}: "
            f"{instance.content[:50]}..."
        )
        
        # Update session last activity if exists
        if instance.session:
            instance.session.last_activity = timezone.now()
            instance.session.save(update_fields=['last_activity'])
        
        # Trigger message processing if not already processed
        if not instance.processed:
            # This could trigger async processing
            from .tasks import process_whatsapp_message
            process_whatsapp_message.delay(instance.id)


@receiver(post_save, sender=WhatsAppCommand)
def handle_command_executed(sender, instance, created, **kwargs):
    """Handle command execution logging and analytics"""
    if created:
        logger.info(
            f"WhatsApp command executed: {instance.command} by {instance.phone_number} "
            f"(Success: {instance.success})"
        )
        
        # Update command usage statistics in cache
        stats_key = f"whatsapp_command_stats:{instance.command}"
        current_count = cache.get(stats_key, 0)
        cache.set(stats_key, current_count + 1, timeout=86400 * 7)  # 7 days
        
        # Track failed commands for monitoring
        if not instance.success:
            error_key = f"whatsapp_command_errors:{timezone.now().date()}"
            error_count = cache.get(error_key, 0)
            cache.set(error_key, error_count + 1, timeout=86400)  # 24 hours
            
            # Log error for monitoring
            logger.error(
                f"WhatsApp command failed: {instance.command} by {instance.phone_number} - "
                f"Error: {instance.error_message}"
            )


@receiver(post_save, sender=WhatsAppNotification)
def handle_notification_status_change(sender, instance, created, **kwargs):
    """Handle notification status changes"""
    if created:
        logger.info(
            f"WhatsApp notification created: {instance.notification_type} "
            f"for {instance.phone_number}"
        )
        
        # Schedule notification if it's time to send
        if instance.scheduled_at <= timezone.now() and instance.status == 'pending':
            from .tasks import send_whatsapp_notification
            send_whatsapp_notification.delay(instance.id)
    
    else:
        # Log status changes
        if instance.status == 'sent':
            logger.info(
                f"WhatsApp notification sent: {instance.id} to {instance.phone_number}"
            )
        elif instance.status == 'failed':
            logger.error(
                f"WhatsApp notification failed: {instance.id} to {instance.phone_number}"
            )


@receiver(post_save, sender=Patient)
def handle_patient_created_for_whatsapp(sender, instance, created, **kwargs):
    if created and instance.phone_number:
        try:
            session = WhatsAppSession.objects.filter(
                phone_number=instance.phone_number,
                is_authenticated=True
            ).first()
            
            if session:
                WhatsAppNotification.objects.create(
                    phone_number=instance.phone_number,
                    notification_type='system_alert',
                    title='Welcome to CARE',
                    message=(
                        f"🏥 Welcome to CARE, {instance.name}!\n\n"
                        "Your patient profile has been created successfully. "
                        "You can now access your medical records, appointments, "
                        "and medications through this WhatsApp bot.\n\n"
                        "Type 'help' to see available commands."
                    ),
                    patient=instance,
                    scheduled_at=timezone.now()
                )
                
                logger.info(
                    f"Welcome notification created for new patient: {instance.name} "
                    f"({instance.phone_number})"
                )
        
        except Exception as e:
            logger.error(
                f"Error creating welcome notification for patient {instance.id}: {e}"
            )


def cleanup_expired_sessions():
    """Clean up expired WhatsApp sessions"""
    expired_sessions = WhatsAppSession.objects.filter(
        session_expires_at__lt=timezone.now(),
        is_authenticated=True
    )
    
    count = expired_sessions.count()
    if count > 0:
        # Update sessions to unauthenticated
        expired_sessions.update(
            is_authenticated=False,
            authenticated_at=None
        )
        
        logger.info(f"Cleaned up {count} expired WhatsApp sessions")
        
        # Clear related cache entries
        for session in expired_sessions:
            cache_key = f"whatsapp_session:{session.phone_number}"
            cache.delete(cache_key)
            
            activity_key = f"whatsapp_activity:{session.phone_number}"
            cache.delete(activity_key)


def cleanup_old_messages(days=30):
    """Clean up old WhatsApp messages"""
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_messages = WhatsAppMessage.objects.filter(
        timestamp__lt=cutoff_date,
        processed=True
    )
    
    count = old_messages.count()
    if count > 0:
        old_messages.delete()
        logger.info(f"Cleaned up {count} old WhatsApp messages (older than {days} days)")


def cleanup_old_commands(days=90):
    """Clean up old command logs"""
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_commands = WhatsAppCommand.objects.filter(
        executed_at__lt=cutoff_date
    )
    
    count = old_commands.count()
    if count > 0:
        old_commands.delete()
        logger.info(f"Cleaned up {count} old WhatsApp commands (older than {days} days)")


def cleanup_old_notifications(days=180):
    """Clean up old notifications"""
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_notifications = WhatsAppNotification.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['sent', 'delivered', 'read', 'failed']
    )
    
    count = old_notifications.count()
    if count > 0:
        old_notifications.delete()
        logger.info(f"Cleaned up {count} old WhatsApp notifications (older than {days} days)")