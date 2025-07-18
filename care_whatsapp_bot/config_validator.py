"""
WhatsApp Configuration Validator
Ensures all required settings are properly configured before the bot starts.
"""
import logging
from typing import Dict, List, Optional
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class WhatsAppConfigValidator:
    """Validates WhatsApp configuration and provides helpful error messages"""
    
    REQUIRED_SETTINGS = [
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID', 
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN',
    ]
    
    OPTIONAL_SETTINGS = [
        'WHATSAPP_APP_SECRET',
        'WHATSAPP_WEBHOOK_URL',
    ]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Dict[str, any]:
        """Run all validation checks"""
        self.errors.clear()
        self.warnings.clear()
        
        self._validate_required_settings()
        self._validate_token_format()
        self._validate_phone_number_id()
        self._validate_api_connectivity()
        
        return {
            'is_valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': self._generate_summary()
        }
    
    def _validate_required_settings(self):
        """Check if all required settings are present"""
        for setting in self.REQUIRED_SETTINGS:
            value = getattr(settings, setting, None)
            if not value or value.strip() == "":
                self.errors.append(f"❌ {setting} is missing or empty")
    
    def _validate_token_format(self):
        """Validate access token format"""
        token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        if token and not token.startswith('EAA'):
            self.warnings.append(f"⚠️ Access token format looks unusual (should start with 'EAA')")
    
    def _validate_phone_number_id(self):
        """Validate phone number ID format"""
        phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        if phone_id and not phone_id.isdigit():
            self.errors.append(f"❌ Phone number ID should be numeric, got: {phone_id}")
    
    def _validate_api_connectivity(self):
        """Test API connectivity with current credentials"""
        try:
            token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
            phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
            
            if not token or not phone_id:
                return  # Skip if basic settings are missing
            
            # Test API endpoint
            url = f"https://graph.facebook.com/v23.0/{phone_id}"
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 401:
                self.errors.append("❌ Access token is invalid or expired")
            elif response.status_code == 404:
                self.errors.append("❌ Phone number ID not found or no permissions")
            elif response.status_code != 200:
                self.warnings.append(f"⚠️ API returned status {response.status_code}")
            else:
                logger.info("✅ WhatsApp API connectivity test passed")
                
        except requests.RequestException as e:
            self.warnings.append(f"⚠️ Could not test API connectivity: {str(e)}")
    
    def _generate_summary(self) -> str:
        """Generate a human-readable summary"""
        if len(self.errors) == 0:
            return "✅ WhatsApp configuration is valid!"
        else:
            return f"❌ Found {len(self.errors)} error(s) and {len(self.warnings)} warning(s)"
    
    def get_setup_instructions(self) -> str:
        """Provide setup instructions for common issues"""
        instructions = []
        
        if any("ACCESS_TOKEN" in error for error in self.errors):
            instructions.append(
                "🔑 To get a new access token:\n"
                "1. Go to Facebook Developers Console\n"
                "2. Select your WhatsApp Business app\n"
                "3. Go to WhatsApp > API Setup\n"
                "4. Generate a new temporary token\n"
                "5. Update WHATSAPP_ACCESS_TOKEN in your .env file"
            )
        
        if any("PHONE_NUMBER_ID" in error for error in self.errors):
            instructions.append(
                "📱 To get your phone number ID:\n"
                "1. In Facebook Developers Console\n"
                "2. Go to WhatsApp > API Setup\n"
                "3. Copy the Phone Number ID\n"
                "4. Update WHATSAPP_PHONE_NUMBER_ID in your .env file"
            )
        
        return "\n\n".join(instructions)


def validate_whatsapp_config() -> Dict[str, any]:
    """Convenience function to validate WhatsApp configuration"""
    validator = WhatsAppConfigValidator()
    return validator.validate_all()