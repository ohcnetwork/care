import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import requests
from django.conf import settings

from .base import BaseIMProvider, IMMessage, IMResponse, MessageType

logger = logging.getLogger(__name__)


class WhatsAppProvider(BaseIMProvider):
    """WhatsApp Business API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get('access_token') or getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.phone_number_id = config.get('phone_number_id') or getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        self.webhook_verify_token = config.get('webhook_verify_token') or getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', None)
        self.app_secret = config.get('app_secret') or getattr(settings, 'WHATSAPP_APP_SECRET', None)
        self.api_version = config.get('api_version', 'v23.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def get_platform_name(self) -> str:
        return "whatsapp"
    
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> Optional[IMMessage]:
        """Parse WhatsApp webhook payload to standardized message format"""
        try:
            entry = raw_data.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            
            messages = value.get('messages', [])
            if not messages:
                return None
            
            message = messages[0]
            sender_id = message.get('from')
            message_id = message.get('id')
            timestamp = message.get('timestamp')
            
            message_type = MessageType.TEXT
            content = ""
            metadata = {
                'message_id': message_id,
                'timestamp': timestamp,
                'raw_data': message
            }
            
            if 'text' in message:
                content = message['text']['body']
                message_type = MessageType.TEXT
            elif 'image' in message:
                message_type = MessageType.IMAGE
                content = message['image'].get('caption', '')
                metadata['media_id'] = message['image']['id']
            elif 'document' in message:
                message_type = MessageType.DOCUMENT
                content = message['document'].get('caption', '')
                metadata['media_id'] = message['document']['id']
                metadata['filename'] = message['document'].get('filename', '')
            elif 'audio' in message:
                message_type = MessageType.AUDIO
                metadata['media_id'] = message['audio']['id']
            elif 'video' in message:
                message_type = MessageType.VIDEO
                content = message['video'].get('caption', '')
                metadata['media_id'] = message['video']['id']
            elif 'location' in message:
                message_type = MessageType.LOCATION
                location = message['location']
                content = f"Latitude: {location.get('latitude')}, Longitude: {location.get('longitude')}"
                metadata['latitude'] = location.get('latitude')
                metadata['longitude'] = location.get('longitude')
            
            return IMMessage(
                sender_id=sender_id,
                message_type=message_type,
                content=content,
                platform=self.platform_name,
                timestamp=timestamp,
                metadata=metadata
            )
        
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing WhatsApp message: {e}")
            return None
    
    def send_message(self, response: IMResponse) -> bool:
        """Send message via WhatsApp Business API"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': response.recipient_id,
            }
            
            if response.message_type == MessageType.TEXT:
                payload['type'] = 'text'
                payload['text'] = {'body': response.content}
            elif response.message_type == MessageType.IMAGE:
                payload['type'] = 'image'
                payload['image'] = {
                    'link': response.metadata.get('image_url'),
                    'caption': response.content
                }
            elif response.message_type == MessageType.DOCUMENT:
                payload['type'] = 'document'
                payload['document'] = {
                    'link': response.metadata.get('document_url'),
                    'caption': response.content,
                    'filename': response.metadata.get('filename', 'document')
                }
            
            if 'buttons' in response.metadata:
                payload['type'] = 'interactive'
                payload['interactive'] = {
                    'type': 'button',
                    'body': {'text': response.content},
                    'action': {
                        'buttons': response.metadata['buttons']
                    }
                }
            
            api_response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            logger.info(f"WhatsApp API Response Status: {api_response.status_code}")
            logger.info(f"WhatsApp API Response Body: {api_response.text}")
            
            api_response.raise_for_status()
            
            logger.info(f"WhatsApp message sent successfully to {response.recipient_id}")
            return True
        
        except requests.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"WhatsApp API Error Response: {e.response.text}")
            return False
    
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Validate WhatsApp webhook signature"""
        if not self.app_secret:
            logger.warning("WhatsApp app secret not configured, skipping signature validation")
            return True
        
        try:
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            expected_signature = hmac.new(
                self.app_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        
        except Exception as e:
            logger.error(f"Error validating WhatsApp webhook signature: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get WhatsApp user profile information"""
        try:
            url = f"{self.base_url}/{user_id}"
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        
        except requests.RequestException as e:
            logger.error(f"Error getting WhatsApp user profile: {e}")
            return {}
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify WhatsApp webhook during setup"""
        if mode == 'subscribe' and token == self.webhook_verify_token:
            return challenge
        return None