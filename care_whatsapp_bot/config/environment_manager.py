"""
Environment-aware Configuration Manager for WhatsApp Bot
Provides robust configuration management with validation and environment detection.
"""
import os
import logging
from typing import Dict, Optional, Any, List
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class ConfigValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    environment: Environment


class WhatsAppEnvironmentManager:
    """Enhanced environment-aware configuration manager"""
    
    def __init__(self):
        self.environment = self._detect_environment()
        self._config_cache = {}
        
    def _detect_environment(self) -> Environment:
        """Detect current environment based on various indicators"""
        # Check explicit environment variable
        env_name = os.getenv('DJANGO_ENVIRONMENT', '').lower()
        if env_name in [e.value for e in Environment]:
            return Environment(env_name)
            
        # Check Django DEBUG setting
        if getattr(settings, 'DEBUG', False):
            return Environment.DEVELOPMENT
            
        # Check domain patterns
        domain = getattr(settings, 'CURRENT_DOMAIN', 'localhost')
        if 'localhost' in domain or '127.0.0.1' in domain:
            return Environment.DEVELOPMENT
        elif 'staging' in domain or 'dev' in domain:
            return Environment.STAGING
        else:
            return Environment.PRODUCTION
    
    def get_required_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get environment-specific required configurations"""
        base_configs = {
            'WHATSAPP_ACCESS_TOKEN': {
                'required': True,
                'validation': self._validate_access_token,
                'description': 'WhatsApp Business API access token'
            },
            'WHATSAPP_PHONE_NUMBER_ID': {
                'required': True,
                'validation': self._validate_phone_number_id,
                'description': 'WhatsApp Business phone number ID'
            },
            'WHATSAPP_WEBHOOK_VERIFY_TOKEN': {
                'required': True,
                'validation': self._validate_verify_token,
                'description': 'Webhook verification token'
            }
        }
        
        if self.environment == Environment.PRODUCTION:
            base_configs.update({
                'WHATSAPP_APP_SECRET': {
                    'required': True,
                    'validation': self._validate_app_secret,
                    'description': 'App secret for webhook signature validation'
                },
                'WHATSAPP_WEBHOOK_URL': {
                    'required': True,
                    'validation': self._validate_webhook_url,
                    'description': 'Public webhook URL'
                }
            })
        
        return base_configs
    
    def validate_configuration(self) -> ConfigValidationResult:
        """Comprehensive configuration validation"""
        errors = []
        warnings = []
        
        required_configs = self.get_required_configs()
        
        for config_key, config_info in required_configs.items():
            value = getattr(settings, config_key, '')
            
            if config_info['required'] and not value:
                errors.append(f"{config_key} is required for {self.environment.value} environment")
                continue
                
            if value and config_info.get('validation'):
                validation_result = config_info['validation'](value)
                if not validation_result['is_valid']:
                    errors.extend(validation_result.get('errors', []))
                warnings.extend(validation_result.get('warnings', []))
        
        # Environment-specific validations
        if self.environment == Environment.PRODUCTION:
            webhook_url = getattr(settings, 'WHATSAPP_WEBHOOK_URL', '')
            if webhook_url and ('localhost' in webhook_url or '127.0.0.1' in webhook_url):
                errors.append("Production environment cannot use localhost webhook URL")
        
        return ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            environment=self.environment
        )
    
    def _validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate access token format and basic structure"""
        errors = []
        warnings = []
        
        if not token.startswith('EAA'):
            errors.append("Access token should start with 'EAA'")
        
        if len(token) < 100:
            warnings.append("Access token seems unusually short")
            
        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_phone_number_id(self, phone_id: str) -> Dict[str, Any]:
        """Validate phone number ID format"""
        errors = []
        warnings = []
        
        if not phone_id.isdigit():
            errors.append("Phone number ID must be numeric")
        
        if len(phone_id) < 10:
            warnings.append("Phone number ID seems unusually short")
            
        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_verify_token(self, token: str) -> Dict[str, Any]:
        """Validate verify token"""
        errors = []
        warnings = []
        
        if len(token) < 8:
            warnings.append("Verify token should be at least 8 characters for security")
            
        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_app_secret(self, secret: str) -> Dict[str, Any]:
        """Validate app secret"""
        errors = []
        warnings = []
        
        if len(secret) < 16:
            warnings.append("App secret seems unusually short")
            
        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def _validate_webhook_url(self, url: str) -> Dict[str, Any]:
        """Validate webhook URL"""
        errors = []
        warnings = []
        
        if not url.startswith('https://'):
            errors.append("Webhook URL must use HTTPS in production")
        
        if 'localhost' in url or '127.0.0.1' in url:
            errors.append("Webhook URL cannot be localhost in production")
            
        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        validation_result = self.validate_configuration()
        
        return {
            'environment': self.environment.value,
            'is_valid': validation_result.is_valid,
            'error_count': len(validation_result.errors),
            'warning_count': len(validation_result.warnings),
            'has_access_token': bool(getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')),
            'has_phone_number_id': bool(getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')),
            'has_app_secret': bool(getattr(settings, 'WHATSAPP_APP_SECRET', '')),
            'webhook_url_configured': bool(getattr(settings, 'WHATSAPP_WEBHOOK_URL', '')),
        }


# Global instance
environment_manager = WhatsAppEnvironmentManager()