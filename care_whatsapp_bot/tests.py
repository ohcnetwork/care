from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from unittest.mock import patch, MagicMock
import json
from datetime import timedelta

from .models import (
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppCommand,
    WhatsAppNotification
)
from .authentication import WhatsAppAuthenticator
from .message_router import MessageRouter
from .im_wrapper.whatsapp import WhatsAppProvider
from .im_wrapper.base import IMMessage, MessageType, IMResponse
from care.emr.models.patient import Patient
from care.emr.models.organization import Organization


class WhatsAppModelTests(TestCase):
    """Test WhatsApp models"""
    
    def setUp(self):
        self.phone_number = "+1234567890"
        self.organization = Organization.objects.create(
            name="Test Hospital",
            org_type="HOSPITAL"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            phone_number=self.phone_number,
            organization=self.organization
        )
    
    def test_whatsapp_session_creation(self):
        """Test WhatsApp session creation"""
        session = WhatsAppSession.objects.create(
            phone_number=self.phone_number,
            user_type='patient',
            patient=self.patient
        )
        
        self.assertEqual(session.phone_number, self.phone_number)
        self.assertEqual(session.user_type, 'patient')
        self.assertEqual(session.patient, self.patient)
        self.assertFalse(session.is_authenticated)
        self.assertTrue(session.is_session_valid() == False)  # Not authenticated
    
    def test_session_authentication(self):
        """Test session authentication"""
        session = WhatsAppSession.objects.create(
            phone_number=self.phone_number,
            user_type='patient',
            patient=self.patient,
            is_authenticated=True,
            authenticated_at=timezone.now()
        )
        
        # Extend session
        session.extend_session(hours=24)
        
        self.assertTrue(session.is_authenticated)
        self.assertTrue(session.is_session_valid())
        self.assertIsNotNone(session.session_expires_at)
    
    def test_whatsapp_message_creation(self):
        """Test WhatsApp message creation"""
        session = WhatsAppSession.objects.create(
            phone_number=self.phone_number,
            user_type='patient'
        )
        
        message = WhatsAppMessage.objects.create(
            phone_number=self.phone_number,
            direction='incoming',
            message_type='text',
            content='Hello',
            timestamp=timezone.now(),
            session=session
        )
        
        self.assertEqual(message.phone_number, self.phone_number)
        self.assertEqual(message.direction, 'incoming')
        self.assertEqual(message.content, 'Hello')
        self.assertFalse(message.processed)
        
        # Test mark processed
        message.mark_processed()
        self.assertTrue(message.processed)
        self.assertIsNotNone(message.processed_at)
    
    def test_whatsapp_notification_creation(self):
        """Test WhatsApp notification creation"""
        notification = WhatsAppNotification.objects.create(
            phone_number=self.phone_number,
            notification_type='appointment_reminder',
            title='Appointment Reminder',
            message='You have an appointment tomorrow',
            patient=self.patient,
            scheduled_at=timezone.now()
        )
        
        self.assertEqual(notification.phone_number, self.phone_number)
        self.assertEqual(notification.status, 'pending')
        
        # Test mark sent
        notification.mark_sent('msg_123')
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(notification.whatsapp_message_id, 'msg_123')
        self.assertIsNotNone(notification.sent_at)


class WhatsAppAuthenticatorTests(TestCase):
    """Test WhatsApp authenticator"""
    
    def setUp(self):
        self.authenticator = WhatsAppAuthenticator()
        self.phone_number = "+1234567890"
        self.organization = Organization.objects.create(
            name="Test Hospital",
            org_type="HOSPITAL"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            phone_number=self.phone_number,
            organization=self.organization
        )
    
    def test_phone_number_normalization(self):
        """Test phone number normalization"""
        test_cases = [
            ("1234567890", "+1234567890"),
            ("+1234567890", "+1234567890"),
            ("91-9876543210", "+919876543210"),
            (" +1 234 567 890 ", "+1234567890")
        ]
        
        for input_phone, expected in test_cases:
            normalized = self.authenticator._normalize_phone_number(input_phone)
            self.assertEqual(normalized, expected)
    
    def test_user_type_identification(self):
        """Test user type identification"""
        # Test patient identification
        user_type = self.authenticator.identify_user_type(self.phone_number)
        self.assertEqual(user_type, 'patient')
        
        # Test unknown user
        unknown_phone = "+9999999999"
        user_type = self.authenticator.identify_user_type(unknown_phone)
        self.assertEqual(user_type, 'unknown')
    
    @patch('care.utils.sms.send_sms.send_sms')
    def test_otp_generation_and_verification(self, mock_send_sms):
        """Test OTP generation and verification"""
        mock_send_sms.return_value = True
        
        # Generate OTP
        result = self.authenticator.generate_otp(self.phone_number)
        self.assertTrue(result['success'])
        
        # Get OTP from cache for testing
        cache_key = f"whatsapp_otp:{self.phone_number}"
        otp_data = cache.get(cache_key)
        self.assertIsNotNone(otp_data)
        
        otp = otp_data['otp']
        
        # Verify correct OTP
        result = self.authenticator.verify_otp(self.phone_number, otp)
        self.assertTrue(result['success'])
        
        # Verify incorrect OTP
        result = self.authenticator.verify_otp(self.phone_number, '000000')
        self.assertFalse(result['success'])
    
    def test_session_management(self):
        """Test session creation and retrieval"""
        # Create session
        session = self.authenticator.create_session(
            self.phone_number, 'patient', patient=self.patient
        )
        
        self.assertEqual(session.phone_number, self.phone_number)
        self.assertEqual(session.user_type, 'patient')
        self.assertEqual(session.patient, self.patient)
        self.assertTrue(session.is_authenticated)
        
        # Get session
        retrieved_session = self.authenticator.get_session(self.phone_number)
        self.assertEqual(retrieved_session.id, session.id)
        
        # Logout
        self.authenticator.logout(self.phone_number)
        logged_out_session = self.authenticator.get_session(self.phone_number)
        self.assertFalse(logged_out_session.is_authenticated)


class WhatsAppProviderTests(TestCase):
    """Test WhatsApp provider"""
    
    def setUp(self):
        self.provider = WhatsAppProvider({})
    
    def test_webhook_signature_validation(self):
        """Test webhook signature validation"""
        # Mock settings
        with patch.object(settings, 'WHATSAPP_APP_SECRET', 'test_secret'):
            payload = '{"test": "data"}'
            
            # Generate valid signature
            import hmac
            import hashlib
            
            signature = hmac.new(
                'test_secret'.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Test valid signature
            is_valid = self.provider.validate_webhook_signature(
                payload, f'sha256={signature}'
            )
            self.assertTrue(is_valid)
            
            # Test invalid signature
            is_valid = self.provider.validate_webhook_signature(
                payload, 'sha256=invalid_signature'
            )
            self.assertFalse(is_valid)
    
    def test_message_parsing(self):
        """Test incoming message parsing"""
        # Test text message
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'id': 'msg_123',
                            'from': '1234567890',
                            'timestamp': '1234567890',
                            'type': 'text',
                            'text': {'body': 'Hello'}
                        }]
                    }
                }]
            }]
        }
        
        messages = self.provider.parse_incoming_message(webhook_data)
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message.message_id, 'msg_123')
        self.assertEqual(message.sender_id, '+1234567890')
        self.assertEqual(message.message_type, MessageType.TEXT)
        self.assertEqual(message.content, 'Hello')


class WhatsAppWebhookViewTests(TestCase):
    """Test WhatsApp webhook views"""
    
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('care_whatsapp_bot:whatsapp_webhook')
    
    def test_webhook_verification(self):
        """Test webhook verification"""
        with patch.object(settings, 'WHATSAPP_VERIFY_TOKEN', 'test_token'):
            response = self.client.get(self.webhook_url, {
                'hub.mode': 'subscribe',
                'hub.challenge': 'test_challenge',
                'hub.verify_token': 'test_token'
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content.decode(), 'test_challenge')
    
    def test_webhook_verification_invalid_token(self):
        """Test webhook verification with invalid token"""
        with patch.object(settings, 'WHATSAPP_VERIFY_TOKEN', 'test_token'):
            response = self.client.get(self.webhook_url, {
                'hub.mode': 'subscribe',
                'hub.challenge': 'test_challenge',
                'hub.verify_token': 'wrong_token'
            })
            
            self.assertEqual(response.status_code, 403)
    
    @patch('care_whatsapp_bot.tasks.process_whatsapp_message.delay')
    @patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.validate_webhook_signature')
    def test_webhook_message_processing(self, mock_validate, mock_task):
        """Test webhook message processing"""
        mock_validate.return_value = True
        
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'id': 'msg_123',
                            'from': '1234567890',
                            'timestamp': '1234567890',
                            'type': 'text',
                            'text': {'body': 'Hello'}
                        }]
                    }
                }]
            }]
        }
        
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(webhook_data),
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=test_signature'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that message was created
        message = WhatsAppMessage.objects.filter(
            whatsapp_message_id='msg_123'
        ).first()
        self.assertIsNotNone(message)
        self.assertEqual(message.content, 'Hello')
        
        # Check that task was called
        mock_task.assert_called_once_with(message.id)
    
    def test_health_check(self):
        """Test health check endpoint"""
        health_url = reverse('care_whatsapp_bot:health_check')
        response = self.client.get(health_url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')


class MessageRouterTests(TestCase):
    """Test message router"""
    
    def setUp(self):
        self.provider = WhatsAppProvider({})
        self.authenticator = WhatsAppAuthenticator()
        self.router = MessageRouter(self.provider, self.authenticator)
        self.phone_number = "+1234567890"
        
        self.organization = Organization.objects.create(
            name="Test Hospital",
            org_type="HOSPITAL"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            phone_number=self.phone_number,
            organization=self.organization
        )
    
    def test_help_command(self):
        """Test help command"""
        message = IMMessage(
            message_id='msg_123',
            sender_id=self.phone_number,
            message_type=MessageType.TEXT,
            content='help',
            timestamp=timezone.now()
        )
        
        response = self.router.route_message(message)
        
        self.assertIsNotNone(response)
        self.assertIn('CARE WhatsApp Bot', response.content)
        self.assertIn('Available commands', response.content)
    
    @patch('care.utils.sms.send_sms.send_sms')
    def test_login_flow(self, mock_send_sms):
        """Test login flow"""
        mock_send_sms.return_value = True
        
        # Test login command
        login_message = IMMessage(
            message_id='msg_123',
            sender_id=self.phone_number,
            message_type=MessageType.TEXT,
            content='login',
            timestamp=timezone.now()
        )
        
        response = self.router.route_message(login_message)
        
        self.assertIsNotNone(response)
        self.assertIn('OTP', response.content)
        
        # Get OTP from cache
        cache_key = f"whatsapp_otp:{self.phone_number}"
        otp_data = cache.get(cache_key)
        self.assertIsNotNone(otp_data)
        
        otp = otp_data['otp']
        
        # Test OTP verification
        otp_message = IMMessage(
            message_id='msg_124',
            sender_id=self.phone_number,
            message_type=MessageType.TEXT,
            content=otp,
            timestamp=timezone.now()
        )
        
        response = self.router.route_message(otp_message)
        
        self.assertIsNotNone(response)
        self.assertIn('successfully', response.content.lower())
        
        # Check session was created
        session = WhatsAppSession.objects.filter(
            phone_number=self.phone_number,
            is_authenticated=True
        ).first()
        self.assertIsNotNone(session)
    
    def test_unauthenticated_command(self):
        """Test command without authentication"""
        message = IMMessage(
            message_id='msg_123',
            sender_id=self.phone_number,
            message_type=MessageType.TEXT,
            content='get records',
            timestamp=timezone.now()
        )
        
        response = self.router.route_message(message)
        
        self.assertIsNotNone(response)
        self.assertIn('login', response.content.lower())


class WhatsAppTaskTests(TestCase):
    """Test WhatsApp Celery tasks"""
    
    def setUp(self):
        self.phone_number = "+1234567890"
        self.organization = Organization.objects.create(
            name="Test Hospital",
            org_type="HOSPITAL"
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            phone_number=self.phone_number,
            organization=self.organization
        )
    
    @patch('care_whatsapp_bot.tasks.MessageRouter')
    @patch('care_whatsapp_bot.tasks.WhatsAppProvider')
    def test_process_whatsapp_message_task(self, mock_provider, mock_router):
        """Test process WhatsApp message task"""
        # Create test message
        message = WhatsAppMessage.objects.create(
            phone_number=self.phone_number,
            direction='incoming',
            message_type='text',
            content='help',
            timestamp=timezone.now()
        )
        
        # Mock router response
        mock_response = IMResponse(content='Help response', message_type='text')
        mock_router_instance = MagicMock()
        mock_router_instance.route_message.return_value = mock_response
        mock_router.return_value = mock_router_instance
        
        # Mock provider
        mock_provider_instance = MagicMock()
        mock_provider_instance.send_message.return_value = {'success': True}
        mock_provider.return_value = mock_provider_instance
        
        # Import and run task
        from .tasks import process_whatsapp_message
        result = process_whatsapp_message(message.id)
        
        self.assertEqual(result['status'], 'success')
        
        # Check message was marked as processed
        message.refresh_from_db()
        self.assertTrue(message.processed)
    
    @patch('care_whatsapp_bot.tasks.WhatsAppProvider')
    def test_send_whatsapp_notification_task(self, mock_provider):
        """Test send WhatsApp notification task"""
        # Create test notification
        notification = WhatsAppNotification.objects.create(
            phone_number=self.phone_number,
            notification_type='appointment_reminder',
            title='Test Notification',
            message='Test message',
            patient=self.patient,
            scheduled_at=timezone.now()
        )
        
        # Mock provider
        mock_provider_instance = MagicMock()
        mock_provider_instance.send_message.return_value = {
            'success': True,
            'message_id': 'msg_123'
        }
        mock_provider.return_value = mock_provider_instance
        
        # Import and run task
        from .tasks import send_whatsapp_notification
        result = send_whatsapp_notification(notification.id)
        
        self.assertEqual(result['status'], 'success')
        
        # Check notification was marked as sent
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'sent')
        self.assertEqual(notification.whatsapp_message_id, 'msg_123')