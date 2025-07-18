"""
Comprehensive Testing Framework for WhatsApp Bot
Provides integration tests, mock services, and test utilities.
"""
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from care_whatsapp_bot.models import WhatsAppSession, WhatsAppMessage
from care_whatsapp_bot.im_wrapper.whatsapp import WhatsAppProvider
from care_whatsapp_bot.message_router import MessageRouter
from care_whatsapp_bot.authentication import WhatsAppAuthenticator
from typing import Dict, Any, Optional

User = get_user_model()


class WhatsAppTestMixin:
    """Mixin providing common WhatsApp testing utilities"""
    
    def setUp(self):
        super().setUp()
        self.phone_number = "+918767341918"
        self.webhook_url = reverse('care_whatsapp_bot:whatsapp_webhook')
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            phone_number=self.phone_number
        )
        
        # Clear cache
        cache.clear()
    
    def create_whatsapp_payload(self, message_text: str, phone_number: str = None, 
                               message_type: str = "text", **kwargs) -> Dict[str, Any]:
        """Create a WhatsApp webhook payload for testing"""
        phone = phone_number or self.phone_number
        message_id = kwargs.get('message_id', f"wamid.test_{uuid.uuid4().hex[:8]}")
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550559999",
                            "phone_number_id": "651347521403933"
                        },
                        "messages": [{
                            "from": phone.lstrip('+'),
                            "id": message_id,
                            "timestamp": str(kwargs.get('timestamp', 1234567890)),
                            "type": message_type
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Add message content based on type
        if message_type == "text":
            payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {
                "body": message_text
            }
        elif message_type == "interactive":
            payload["entry"][0]["changes"][0]["value"]["messages"][0]["interactive"] = {
                "type": "button_reply",
                "button_reply": {
                    "id": kwargs.get('button_id', 'btn_1'),
                    "title": message_text
                }
            }
        
        return payload
    
    def mock_whatsapp_api_success(self, message_id: str = "msg_test_123"):
        """Mock successful WhatsApp API response"""
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": self.phone_number, "wa_id": self.phone_number.lstrip('+')}],
            "messages": [{"id": message_id}]
        }
    
    def mock_whatsapp_api_error(self, error_code: int = 190, error_message: str = "Token expired"):
        """Mock WhatsApp API error response"""
        return {
            "error": {
                "message": error_message,
                "type": "OAuthException",
                "code": error_code,
                "fbtrace_id": f"test_trace_{uuid.uuid4().hex[:8]}"
            }
        }


class WhatsAppIntegrationTestCase(WhatsAppTestMixin, TestCase):
    """Integration tests for WhatsApp bot functionality"""
    
    @patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message')
    def test_complete_registration_flow(self, mock_send):
        """Test complete user registration flow"""
        mock_send.return_value = self.mock_whatsapp_api_success()
        
        # Step 1: User sends "register"
        payload = self.create_whatsapp_payload("register")
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify session created
        session = WhatsAppSession.objects.get(phone_number=self.phone_number)
        self.assertEqual(session.state, 'REGISTRATION_NAME')
        
        # Verify OTP sent
        mock_send.assert_called()
        
        # Step 2: User provides name
        payload = self.create_whatsapp_payload("John Doe")
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        session.refresh_from_db()
        self.assertEqual(session.state, 'REGISTRATION_OTP')
        
        # Step 3: User provides OTP
        # Get the OTP from cache
        otp_key = f"whatsapp_otp:{self.phone_number}"
        otp = cache.get(otp_key)
        self.assertIsNotNone(otp)
        
        payload = self.create_whatsapp_payload(otp)
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        session.refresh_from_db()
        self.assertEqual(session.state, 'AUTHENTICATED')
    
    @patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message')
    def test_menu_navigation(self, mock_send):
        """Test menu navigation functionality"""
        mock_send.return_value = self.mock_whatsapp_api_success()
        
        # Create authenticated session
        session = WhatsAppSession.objects.create(
            phone_number=self.phone_number,
            user=self.user,
            state='AUTHENTICATED'
        )
        
        # Test menu command
        payload = self.create_whatsapp_payload("menu")
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called()
        
        # Verify menu message sent
        call_args = mock_send.call_args[0][0]
        self.assertIn("Main Menu", call_args['text'])
    
    @patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message')
    def test_error_handling(self, mock_send):
        """Test error handling scenarios"""
        # Mock API error
        mock_send.side_effect = Exception("Network error")
        
        payload = self.create_whatsapp_payload("test")
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should still return 200 to WhatsApp
        self.assertEqual(response.status_code, 200)
        
        # Verify error was logged (would need to check logs in real scenario)
        mock_send.assert_called()


class WhatsAppProviderTestCase(WhatsAppTestMixin, TestCase):
    """Unit tests for WhatsApp provider"""
    
    def setUp(self):
        super().setUp()
        self.provider = WhatsAppProvider({
            'access_token': 'test_token',
            'phone_number_id': '123456789',
            'webhook_verify_token': 'test_verify'
        })
    
    def test_message_parsing(self):
        """Test parsing of incoming WhatsApp messages"""
        payload = self.create_whatsapp_payload("Hello World")
        
        message = self.provider.parse_incoming_message(payload)
        
        self.assertEqual(message.sender, self.phone_number.lstrip('+'))
        self.assertEqual(message.text, "Hello World")
        self.assertEqual(message.message_type.value, "text")
    
    def test_webhook_verification(self):
        """Test webhook verification logic"""
        # Valid verification
        challenge = self.provider.verify_webhook(
            mode="subscribe",
            token="test_verify",
            challenge="test_challenge"
        )
        self.assertEqual(challenge, "test_challenge")
        
        # Invalid token
        challenge = self.provider.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="test_challenge"
        )
        self.assertIsNone(challenge)
    
    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_whatsapp_api_success()
        mock_post.return_value = mock_response
        
        message = {
            'to': self.phone_number.lstrip('+'),
            'text': 'Test message'
        }
        
        result = self.provider.send_message(message)
        
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_message_error(self, mock_post):
        """Test message sending error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = self.mock_whatsapp_api_error()
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_post.return_value = mock_response
        
        message = {
            'to': self.phone_number.lstrip('+'),
            'text': 'Test message'
        }
        
        with self.assertRaises(Exception):
            self.provider.send_message(message)


class WhatsAppLoadTestCase(WhatsAppTestMixin, TransactionTestCase):
    """Load testing for WhatsApp bot"""
    
    @patch('care_whatsapp_bot.im_wrapper.whatsapp.WhatsAppProvider.send_message')
    def test_concurrent_messages(self, mock_send):
        """Test handling of concurrent messages"""
        import threading
        import time
        
        mock_send.return_value = self.mock_whatsapp_api_success()
        
        def send_message(phone_suffix):
            phone = f"+91876734{phone_suffix:04d}"
            payload = self.create_whatsapp_payload("register", phone_number=phone)
            
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type='application/json'
            )
            return response.status_code
        
        # Send 10 concurrent messages
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda i=i: results.append(send_message(i)))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should succeed
        self.assertEqual(len(results), 10)
        self.assertTrue(all(status == 200 for status in results))


class WhatsAppMockService:
    """Mock WhatsApp service for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.webhook_calls = []
    
    def mock_send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Mock message sending"""
        self.sent_messages.append(message)
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": message['to'], "wa_id": message['to']}],
            "messages": [{"id": f"msg_mock_{len(self.sent_messages)}"}]
        }
    
    def simulate_incoming_message(self, phone_number: str, message_text: str, 
                                 webhook_url: str) -> Dict[str, Any]:
        """Simulate incoming message from WhatsApp"""
        import requests
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "MOCK_BUSINESS_ACCOUNT",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550559999",
                            "phone_number_id": "123456789"
                        },
                        "messages": [{
                            "from": phone_number.lstrip('+'),
                            "id": f"mock_msg_{uuid.uuid4().hex[:8]}",
                            "timestamp": "1234567890",
                            "text": {"body": message_text},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        self.webhook_calls.append(payload)
        
        # In real testing, this would make HTTP request
        # For unit tests, return the payload
        return payload
    
    def get_sent_messages(self) -> list:
        """Get all sent messages"""
        return self.sent_messages.copy()
    
    def clear_history(self):
        """Clear message history"""
        self.sent_messages.clear()
        self.webhook_calls.clear()


# Test utilities
def create_test_session(phone_number: str, state: str = 'AUTHENTICATED', user: User = None) -> WhatsAppSession:
    """Create a test WhatsApp session"""
    if not user:
        user = User.objects.create_user(
            username=f"test_{phone_number.replace('+', '')}",
            phone_number=phone_number
        )
    
    return WhatsAppSession.objects.create(
        phone_number=phone_number,
        user=user,
        state=state
    )


def create_test_message(session: WhatsAppSession, message_text: str, 
                       direction: str = 'INCOMING') -> WhatsAppMessage:
    """Create a test WhatsApp message"""
    return WhatsAppMessage.objects.create(
        session=session,
        whatsapp_message_id=f"test_msg_{uuid.uuid4().hex[:8]}",
        direction=direction,
        message_type='TEXT',
        content={'text': message_text},
        timestamp=1234567890
    )