"""
Enhanced WhatsApp Configuration Manager
Provides environment-aware configuration with validation and fallbacks.
"""
import os
import logging
from typing import Dict, Optional, Any
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class WhatsAppConfigManager:
    """Manages WhatsApp configuration with environment awareness"""
    
    def __init__(self):
        self.environment = self._detect_environment()
        self._config_cache = {}
    
    def _detect_environment(self) -> str:
        """Detect current environment"""
        if getattr(settings, 'DEBUG', False):
            return 'development'
        elif os.getenv('ENVIRONMENT') == 'staging':
            return 'staging'
        else:
            return 'production'
    
    def get_webhook_url(self) -> str:
        """Get appropriate webhook URL for current environment"""
        if self.environment == 'development':
            # For local development, use localhost
            return getattr(settings, 'WHATSAPP_WEBHOOK_URL', 
                          'http://localhost:8000/api/care_whatsapp_bot/webhook/')
        else:
            # For production/staging, use configured URL
            webhook_url = getattr(settings, 'WHATSAPP_WEBHOOK_URL', None)
            if not webhook_url:
                raise ImproperlyConfigured(
                    "WHATSAPP_WEBHOOK_URL must be set for production environment"
                )
            return webhook_url
    
    def get_phone_number_id(self) -> str:
        """Get phone number ID with validation"""
        phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        if not phone_id:
            raise ImproperlyConfigured("WHATSAPP_PHONE_NUMBER_ID is required")
        
        # Validate format
        if not phone_id.isdigit():
            raise ImproperlyConfigured(
                f"WHATSAPP_PHONE_NUMBER_ID must be numeric, got: {phone_id}"
            )
        
        return phone_id
    
    def get_access_token(self) -> str:
        """Get access token with validation"""
        token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        if not token:
            raise ImproperlyConfigured("WHATSAPP_ACCESS_TOKEN is required")
        
        # Basic format validation
        if not token.startswith('EAA'):
            logger.warning(
                "Access token format looks unusual - should start with 'EAA'"
            )
        
        return token
    
    def get_verify_token(self) -> str:
        """Get webhook verify token"""
        return getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 
                      getattr(settings, 'WHATSAPP_VERIFY_TOKEN', ''))
    
    def get_app_secret(self) -> Optional[str]:
        """Get app secret (optional but recommended for production)"""
        secret = getattr(settings, 'WHATSAPP_APP_SECRET', None)
        if not secret and self.environment == 'production':
            logger.warning(
                "WHATSAPP_APP_SECRET not set - webhook signature validation disabled"
            )
        return secret
    
    def get_api_version(self) -> str:
        """Get WhatsApp API version"""
        return getattr(settings, 'WHATSAPP_API_VERSION', 'v23.0')
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'environment': self.environment,
            'webhook_url': self.get_webhook_url(),
            'phone_number_id': self.get_phone_number_id(),
            'has_access_token': bool(getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')),
            'has_app_secret': bool(self.get_app_secret()),
            'api_version': self.get_api_version(),
            'verify_token_set': bool(self.get_verify_token()),
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate all configuration and return status"""
        errors = []
        warnings = []
        
        try:
            self.get_phone_number_id()
        except ImproperlyConfigured as e:
            errors.append(str(e))
        
        try:
            self.get_access_token()
        except ImproperlyConfigured as e:
            errors.append(str(e))
        
        if not self.get_verify_token():
            errors.append("WHATSAPP_VERIFY_TOKEN is required")
        
        if not self.get_app_secret() and self.environment == 'production':
            warnings.append("WHATSAPP_APP_SECRET recommended for production")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'environment': self.environment,
            'config_summary': self.get_config_summary()
        }


# Global instance
config_manager = WhatsAppConfigManager()