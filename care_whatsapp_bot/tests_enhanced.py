"""
Comprehensive test suite for WhatsApp bot functionality
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from care_whatsapp_bot.models import WhatsAppSession, WhatsAppMessage
from care_whatsapp_bot.message_router import MessageRouter
from care_whatsapp_bot.im_wrapper.base import IMMessage, MessageType
from care_whatsapp_bot.command_types import CommandType

User = get_user_model()


class WhatsAppBotTestCase(TestCase):
    """Comprehensive test suite for WhatsApp bot"""
    
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('whatsapp_webhook')
        self.router = MessageRouter()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='test_patient_919876543210',
            phone_number='919876543210',
            user_type=5,  # Patient
            first_name='Test',
            last_name='User'
        )
    
    def _create_webhook_payload(self, phone_number: str, message: str):
        """Helper to create WhatsApp webhook payload"""
        return {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "ENTRY_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550559999",
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "messages": [{
                            "from": phone_number,
                            "id": f"wamid.test_{message.replace(' ', '_')}",
                            "timestamp": "1640995200",
                            "text": {"body": message},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
    
    def test_registration_flow(self):
        """Test complete registration flow"""
        phone_number = "919999888777"
        
        # Test registration command
        payload = self._create_webhook_payload(phone_number, "register")
        
        with patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Check if user was created
            new_user = User.objects.filter(username=f'patient_{phone_number}').first()
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.phone_number, phone_number)
            self.assertEqual(new_user.user_type, 5)  # Patient type
    
    def test_login_flow_existing_user(self):
        """Test login flow for existing user"""
        phone_number = "919876543210"
        
        payload = self._create_webhook_payload(phone_number, "login")
        
        with patch('care_whatsapp_bot.authentication.WhatsAppAuthenticator.generate_otp') as mock_otp:
            mock_otp.return_value = "123456"
            
            with patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message') as mock_send:
                mock_send.return_value = True
                
                response = self.client.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                self.assertEqual(response.status_code, 200)
                mock_otp.assert_called_once_with(phone_number)
    
    def test_otp_verification(self):
        """Test OTP verification flow"""
        phone_number = "919876543210"
        
        # First, simulate login to generate OTP
        with patch('care_whatsapp_bot.authentication.WhatsAppAuthenticator.generate_otp') as mock_gen_otp:
            mock_gen_otp.return_value = "123456"
            self.router.authenticator.generate_otp(phone_number)
        
        # Now test OTP verification
        payload = self._create_webhook_payload(phone_number, "123456")
        
        with patch('care_whatsapp_bot.authentication.WhatsAppAuthenticator.verify_otp') as mock_verify:
            mock_verify.return_value = True
            
            with patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message') as mock_send:
                mock_send.return_value = True
                
                response = self.client.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                self.assertEqual(response.status_code, 200)
                mock_verify.assert_called_once_with(phone_number, "123456")
    
    def test_unregistered_user_login(self):
        """Test login attempt by unregistered user"""
        phone_number = "919999999999"  # Non-existent user
        
        payload = self._create_webhook_payload(phone_number, "login")
        
        with patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Should receive message about registration
            mock_send.assert_called()
            call_args = mock_send.call_args[0][0]  # First argument of first call
            self.assertIn("register", call_args.content.lower())
    
    def test_help_command(self):
        """Test help command functionality"""
        phone_number = "919876543210"
        
        payload = self._create_webhook_payload(phone_number, "help")
        
        with patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            mock_send.assert_called()
    
    def test_webhook_verification(self):
        """Test webhook verification endpoint"""
        response = self.client.get(
            self.webhook_url,
            {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'GSoC2025CareBot',  # From settings
                'hub.challenge': 'test_challenge'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'test_challenge')
    
    def test_invalid_webhook_verification(self):
        """Test webhook verification with invalid token"""
        response = self.client.get(
            self.webhook_url,
            {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'invalid_token',
                'hub.challenge': 'test_challenge'
            }
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_message_router_command_parsing(self):
        """Test message router command parsing"""
        test_cases = [
            ("register", CommandType.REGISTER),
            ("signup", CommandType.REGISTER),
            ("login", CommandType.LOGIN),
            ("help", CommandType.HELP),
            ("123456", CommandType.VERIFY),
            ("unknown command", CommandType.UNKNOWN),
        ]
        
        for message_text, expected_command in test_cases:
            command_type, args = self.router._parse_command(message_text)
            self.assertEqual(command_type, expected_command, 
                           f"Failed for message: '{message_text}'")
    
    def test_session_management(self):
        """Test WhatsApp session creation and management"""
        phone_number = "919876543210"
        
        # Create session
        session = WhatsAppSession.objects.create(
            phone_number=phone_number,
            staff_user=self.test_user,
            is_authenticated=True
        )
        
        self.assertEqual(session.phone_number, phone_number)
        self.assertTrue(session.is_authenticated)
        self.assertEqual(session.staff_user, self.test_user)
    
    def test_message_logging(self):
        """Test message logging functionality"""
        phone_number = "919876543210"
        
        message = WhatsAppMessage.objects.create(
            phone_number=phone_number,
            message_type='text',
            content='Test message',
            direction='incoming'
        )
        
        self.assertEqual(message.phone_number, phone_number)
        self.assertEqual(message.content, 'Test message')
        self.assertEqual(message.direction, 'incoming')


class WhatsAppConfigValidatorTestCase(TestCase):
    """Test configuration validator"""
    
    @patch('care_whatsapp_bot.config_validator.settings')
    def test_valid_configuration(self, mock_settings):
        """Test with valid configuration"""
        mock_settings.WHATSAPP_ACCESS_TOKEN = 'EAAtest_token'
        mock_settings.WHATSAPP_PHONE_NUMBER_ID = '123456789'
        mock_settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN = 'test_token'
        
        from care_whatsapp_bot.config_validator import validate_whatsapp_config
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            result = validate_whatsapp_config()
            self.assertTrue(result['is_valid'])
            self.assertEqual(len(result['errors']), 0)
    
    @patch('care_whatsapp_bot.config_validator.settings')
    def test_missing_configuration(self, mock_settings):
        """Test with missing configuration"""
        mock_settings.WHATSAPP_ACCESS_TOKEN = ''
        mock_settings.WHATSAPP_PHONE_NUMBER_ID = ''
        mock_settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN = ''
        
        from care_whatsapp_bot.config_validator import validate_whatsapp_config
        
        result = validate_whatsapp_config()
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)