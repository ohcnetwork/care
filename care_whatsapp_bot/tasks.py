from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging
import time
from datetime import timedelta

from .models import (
    WhatsAppMessage,
    WhatsAppNotification,
    WhatsAppSession,
    WhatsAppCommand
)
from .message_router import MessageRouter
from .im_wrapper.whatsapp import WhatsAppProvider
from .authentication import WhatsAppAuthenticator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_whatsapp_message(self, message_id):
    """Process incoming WhatsApp message asynchronously"""
    start_time = time.time()
    
    try:
        message = WhatsAppMessage.objects.get(id=message_id)
        
        if message.processed:
            logger.info(f"Message {message_id} already processed")
            return
        
        logger.info(f"Processing WhatsApp message {message_id} from {message.phone_number}")
        
        whatsapp_provider = WhatsAppProvider({})
        authenticator = WhatsAppAuthenticator()
        router = MessageRouter(whatsapp_provider, authenticator)
        
        from .im_wrapper.base import IMMessage, MessageType
        
        message_type_map = {
            'text': MessageType.TEXT,
            'image': MessageType.IMAGE,
            'document': MessageType.DOCUMENT,
            'audio': MessageType.AUDIO,
            'video': MessageType.VIDEO,
            'location': MessageType.LOCATION,
        }
        
        im_message = IMMessage(
            message_id=message.whatsapp_message_id or str(message.id),
            sender_id=message.phone_number,
            message_type=message_type_map.get(message.message_type, MessageType.TEXT),
            content=message.content,
            timestamp=message.timestamp,
            metadata=message.metadata
        )
        
        response = router.route_message(im_message)
        
        if response:
            whatsapp_provider.send_message(
                phone_number=message.phone_number,
                response=response
            )
            
            WhatsAppMessage.objects.create(
                phone_number=message.phone_number,
                direction='outgoing',
                message_type='text',
                content=response.content,
                timestamp=timezone.now(),
                processed=True,
                session=message.session
            )
        
        execution_time = int((time.time() - start_time) * 1000)
        message.mark_processed()
        
        logger.info(
            f"Successfully processed WhatsApp message {message_id} "
            f"in {execution_time}ms"
        )
        
        return {
            'status': 'success',
            'message_id': message_id,
            'execution_time_ms': execution_time
        }
    
    except WhatsAppMessage.DoesNotExist:
        logger.error(f"WhatsApp message {message_id} not found")
        return {'status': 'error', 'message': 'Message not found'}
    
    except Exception as e:
        logger.error(f"Error processing WhatsApp message {message_id}: {e}")
        
        try:
            message = WhatsAppMessage.objects.get(id=message_id)
            message.mark_processed(error=str(e))
        except:
            pass
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            logger.info(f"Retrying message {message_id} in {countdown} seconds")
            raise self.retry(countdown=countdown, exc=e)
        
        return {
            'status': 'error',
            'message_id': message_id,
            'error': str(e)
        }


@shared_task(bind=True, max_retries=3)
def send_whatsapp_notification(self, notification_id):
    """Send WhatsApp notification asynchronously"""
    try:
        notification = WhatsAppNotification.objects.get(id=notification_id)
        
        if notification.status != 'pending':
            logger.info(f"Notification {notification_id} already processed")
            return
        
        logger.info(
            f"Sending WhatsApp notification {notification_id} "
            f"to {notification.phone_number}"
        )
        
        whatsapp_provider = WhatsAppProvider({})
        
        from .im_wrapper.base import IMResponse
        
        response = IMResponse(
            content=f"📢 {notification.title}\n\n{notification.message}",
            message_type='text'
        )
        
        result = whatsapp_provider.send_message(
            phone_number=notification.phone_number,
            response=response
        )
        
        if result and result.get('success'):
            notification.mark_sent(
                whatsapp_message_id=result.get('message_id')
            )
            
            WhatsAppMessage.objects.create(
                phone_number=notification.phone_number,
                direction='outgoing',
                message_type='text',
                content=response.content,
                timestamp=timezone.now(),
                processed=True,
                metadata={'notification_id': notification_id}
            )
            
            logger.info(f"Successfully sent WhatsApp notification {notification_id}")
            
            return {
                'status': 'success',
                'notification_id': notification_id,
                'message_id': result.get('message_id')
            }
        else:
            raise Exception(f"Failed to send notification: {result}")
    
    except WhatsAppNotification.DoesNotExist:
        logger.error(f"WhatsApp notification {notification_id} not found")
        return {'status': 'error', 'message': 'Notification not found'}
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp notification {notification_id}: {e}")
        
        try:
            notification = WhatsAppNotification.objects.get(id=notification_id)
            notification.status = 'failed'
            notification.save(update_fields=['status'])
        except:
            pass
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            logger.info(f"Retrying notification {notification_id} in {countdown} seconds")
            raise self.retry(countdown=countdown, exc=e)
        
        return {
            'status': 'error',
            'notification_id': notification_id,
            'error': str(e)
        }


@shared_task
def cleanup_whatsapp_data():
    """Periodic cleanup of WhatsApp data"""
    logger.info("Starting WhatsApp data cleanup")
    
    from .signals import (
        cleanup_expired_sessions,
        cleanup_old_messages,
        cleanup_old_commands,
        cleanup_old_notifications
    )
    
    try:
        cleanup_expired_sessions()
        cleanup_old_messages(days=30)
        cleanup_old_commands(days=90)
        cleanup_old_notifications(days=180)
        
        logger.info("WhatsApp data cleanup completed successfully")
        
        return {'status': 'success', 'message': 'Cleanup completed'}
    
    except Exception as e:
        logger.error(f"Error during WhatsApp data cleanup: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def send_scheduled_notifications():
    """Send scheduled WhatsApp notifications"""
    logger.info("Checking for scheduled WhatsApp notifications")
    
    try:
        due_notifications = WhatsAppNotification.objects.filter(
            status='pending',
            scheduled_at__lte=timezone.now()
        ).order_by('scheduled_at')[:100]
        
        count = due_notifications.count()
        if count == 0:
            logger.info("No scheduled notifications to send")
            return {'status': 'success', 'sent': 0}
        
        logger.info(f"Found {count} scheduled notifications to send")
        
        sent_count = 0
        for notification in due_notifications:
            try:
                send_whatsapp_notification.delay(notification.id)
                sent_count += 1
            except Exception as e:
                logger.error(
                    f"Error queuing notification {notification.id}: {e}"
                )
        
        logger.info(f"Queued {sent_count} notifications for sending")
        
        return {
            'status': 'success',
            'found': count,
            'queued': sent_count
        }
    
    except Exception as e:
        logger.error(f"Error checking scheduled notifications: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def generate_whatsapp_analytics():
    """Generate WhatsApp usage analytics"""
    logger.info("Generating WhatsApp analytics")
    
    try:
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        total_sessions = WhatsAppSession.objects.count()
        active_sessions = WhatsAppSession.objects.filter(
            is_authenticated=True,
            last_activity__gte=now - timedelta(hours=24)
        ).count()
        messages_today = WhatsAppMessage.objects.filter(
            timestamp__date=today
        ).count()
        
        messages_week = WhatsAppMessage.objects.filter(
            timestamp__date__gte=week_ago
        ).count()
        
        popular_commands = WhatsAppCommand.objects.filter(
            executed_at__date__gte=week_ago
        ).values('command').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        failed_commands = WhatsAppCommand.objects.filter(
            executed_at__date__gte=week_ago,
            success=False
        ).count()
        
        notifications_sent = WhatsAppNotification.objects.filter(
            sent_at__date__gte=week_ago,
            status='sent'
        ).count()
        
        analytics = {
            'generated_at': now.isoformat(),
            'sessions': {
                'total': total_sessions,
                'active_24h': active_sessions
            },
            'messages': {
                'today': messages_today,
                'week': messages_week
            },
            'commands': {
                'popular': list(popular_commands),
                'failed_week': failed_commands
            },
            'notifications': {
                'sent_week': notifications_sent
            }
        }
        
        cache.set('whatsapp_analytics', analytics, timeout=3600)
        
        logger.info("WhatsApp analytics generated successfully")
        
        return {
            'status': 'success',
            'analytics': analytics
        }
    
    except Exception as e:
        logger.error(f"Error generating WhatsApp analytics: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def sync_patient_phone_numbers():
    """Sync patient phone numbers with WhatsApp sessions"""
    logger.info("Syncing patient phone numbers with WhatsApp sessions")
    
    try:
        from care.emr.models.patient import Patient
        
        unlinked_sessions = WhatsAppSession.objects.filter(
            user_type='patient',
            patient__isnull=True
        )
        
        linked_count = 0
        for session in unlinked_sessions:
            try:
                patient = Patient.objects.filter(
                    phone_number=session.phone_number
                ).first()
                
                if patient:
                    session.patient = patient
                    session.save(update_fields=['patient'])
                    linked_count += 1
                    
                    logger.info(
                        f"Linked WhatsApp session {session.id} "
                        f"to patient {patient.id}"
                    )
            
            except Exception as e:
                logger.error(
                    f"Error linking session {session.id}: {e}"
                )
        
        logger.info(f"Linked {linked_count} WhatsApp sessions to patients")
        
        return {
            'status': 'success',
            'linked': linked_count
        }
    
    except Exception as e:
        logger.error(f"Error syncing patient phone numbers: {e}")
        return {'status': 'error', 'error': str(e)}