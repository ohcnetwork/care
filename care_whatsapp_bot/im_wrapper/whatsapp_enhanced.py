"""
Enhanced WhatsApp Provider with better error handling and resilience
"""
import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

import requests
from django.conf import settings
from django.core.cache import cache

from .base import BaseIMProvider, IMMessage, IMResponse, MessageType

logger = logging.getLogger(__name__)


class WhatsAppProviderEnhanced(BaseIMProvider):
    """Enhanced WhatsApp Business API provider with better error handling"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get('access_token') or getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.phone_number_id = config.get('phone_number_id') or getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        self.webhook_verify_token = config.get('webhook_verify_token') or getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', None)
        self.app_secret = config.get('app_secret') or getattr(settings, 'WHATSAPP_APP_SECRET', None)
        self.api_version = config.get('api_version', 'v23.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Enhanced configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1)  # seconds
        self.timeout = config.get('timeout', 30)
        self.rate_limit_cache_key = 'whatsapp_rate_limit'
        
        # Validate configuration on initialization
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration and log warnings"""
        missing_configs = []
        
        if not self.access_token:
            missing_configs.append('WHATSAPP_ACCESS_TOKEN')
        if not self.phone_number_id:
            missing_configs.append('WHATSAPP_PHONE_NUMBER_ID')
        if not self.webhook_verify_token:
            missing_configs.append('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
            
        if missing_configs:
            logger.error(f"Missing WhatsApp configuration: {', '.join(missing_configs)}")
            logger.error("WhatsApp functionality will be limited. Please check your environment variables.")
    
    def _is_rate_limited(self) -> bool:
        """Check if we're currently rate limited"""
        return cache.get(self.rate_limit_cache_key, False)
    
    def _set_rate_limit(self, duration: int = 60):
        """Set rate limit flag"""
        cache.set(self.rate_limit_cache_key, True, duration)
        logger.warning(f"Rate limit activated for {duration} seconds")
    
    def _handle_api_error(self, response: requests.Response) -> Dict[str, Any]:
        """Enhanced API error handling with specific error codes"""
        try:
            error_data = response.json()
            error_info = error_data.get('error', {})
            error_code = error_info.get('code')
            error_subcode = error_info.get('error_subcode')
            error_message = error_info.get('message', 'Unknown error')
            
            # Handle specific error codes
            if error_code == 100:  # Invalid parameter
                if 'does not exist' in error_message:
                    logger.error("❌ Phone Number ID is invalid or doesn't exist")
                elif 'missing permissions' in error_message:
                    logger.error("❌ Access token lacks required permissions")
                else:
                    logger.error(f"❌ API parameter error: {error_message}")
            elif error_code == 190:  # Access token issues
                logger.error("❌ Access token is invalid, expired, or malformed")
            elif error_code == 200:  # Permission denied
                logger.error("❌ Permission denied - check app permissions")
            elif error_code == 4:  # Rate limiting
                self._set_rate_limit(300)  # 5 minutes
                logger.error("❌ Rate limited by WhatsApp API")
            else:
                logger.error(f"❌ WhatsApp API error {error_code}: {error_message}")
            
            return {
                'success': False,
                'error_code': error_code,
                'error_subcode': error_subcode,
                'error_message': error_message,
                'retry_after': 300 if error_code == 4 else 0
            }
            
        except (json.JSONDecodeError, KeyError):
            logger.error(f"❌ Unexpected API response: {response.text}")
            return {
                'success': False,
                'error_code': response.status_code,
                'error_message': f"HTTP {response.status_code}: {response.text}",
                'retry_after': 0
            }
    
    def send_message_with_retry(self, response: IMResponse) -> Dict[str, Any]:
        """Send message with retry logic and better error handling"""
        if self._is_rate_limited():
            logger.warning("Skipping message send due to rate limiting")
            return {'success': False, 'error': 'Rate limited'}
        
        if not self.access_token or not self.phone_number_id:
            logger.error("Cannot send message: Missing WhatsApp configuration")
            return {'success': False, 'error': 'Missing configuration'}
        
        for attempt in range(self.max_retries):
            try:
                result = self._send_message_attempt(response)
                if result['success']:
                    return result
                
                # Handle retryable errors
                if result.get('retry_after', 0) > 0:
                    time.sleep(result['retry_after'])
                elif attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
        
        logger.error(f"Failed to send message after {self.max_retries} attempts")
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def _send_message_attempt(self, response: IMResponse) -> Dict[str, Any]:
        """Single attempt to send a message"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': response.recipient_id,
        }
        
        # Build payload based on message type
        if response.message_type == MessageType.TEXT:
            payload['type'] = 'text'
            payload['text'] = {'body': response.content}
        elif response.message_type == MessageType.IMAGE:
            payload['type'] = 'image'
            payload['image'] = {
                'link': response.metadata.get('image_url'),
                'caption': response.content
            }
        
        # Add interactive elements if present
        if 'buttons' in response.metadata:
            payload['type'] = 'interactive'
            payload['interactive'] = {
                'type': 'button',
                'body': {'text': response.content},
                'action': {
                    'buttons': response.metadata['buttons']
                }
            }
        
        api_response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        
        if api_response.status_code == 200:
            logger.info(f"✅ WhatsApp message sent successfully to {response.recipient_id}")
            return {'success': True, 'response': api_response.json()}
        else:
            return self._handle_api_error(api_response)
    
    def get_platform_name(self) -> str:
        return "whatsapp"
    
    # ... (keep existing methods like parse_incoming_message, validate_webhook_signature, etc.)