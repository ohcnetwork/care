#!/usr/bin/env python
import os
import sys
import django
import logging
import json
from unittest.mock import patch

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

# Now we can import Django models
from django.conf import settings
from django.core.cache import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporarily override settings
original_use_sms = settings.USE_SMS
settings.USE_SMS = True

from care_whatsapp_bot.authentication import WhatsAppAuthenticator

# Mock the mobile_validator function to always pass validation
def mock_mobile_validator(phone_number):
    logger.info(f"MOCK VALIDATOR: Validating phone number {phone_number}")
    return True

def format_indian_mobile(phone_number):
    """Format phone number to match Indian mobile number requirements: +91XXXXXXXXXX"""
    # Remove any non-digit characters except the leading +
    if phone_number.startswith('+'):
        digits_only = '+' + ''.join(filter(str.isdigit, phone_number[1:]))
    else:
        digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different cases
    if len(digits_only) == 10:  # Just the 10-digit number
        return f"+91{digits_only}"
    elif digits_only.startswith('+91') and len(digits_only) == 13:
        return digits_only
    elif digits_only.startswith('91') and len(digits_only) == 12:
        return f"+{digits_only}"
    elif len(digits_only) > 10:
        # If it's longer than 10 digits but doesn't start with 91, 
        # take the last 10 digits and add +91
        return f"+91{digits_only[-10:]}"
    else:
        # If it's shorter than 10 digits, it's invalid
        logger.error(f"Invalid phone number format: {phone_number}")
        return None

def verify_otp(phone_number, otp):
    # Format phone number correctly for Indian mobile
    formatted_phone = format_indian_mobile(phone_number)
    if not formatted_phone:
        logger.error(f"Could not format phone number: {phone_number}")
        return False
    
    logger.info(f"Using phone number: {formatted_phone}")
    
    # Patch the mobile_validator
    with patch('care.utils.models.validators.mobile_validator', mock_mobile_validator):
        auth = WhatsAppAuthenticator()
        
        # Get normalized phone number
        normalized_phone = auth._normalize_phone_number(formatted_phone)
        logger.info(f"Normalized phone by WhatsAppAuthenticator: {normalized_phone}")
        
        # Debug cache keys
        otp_key = auth._get_cache_key(normalized_phone, "otp")
        attempts_key = auth._get_cache_key(normalized_phone, "attempts")
        rate_limit_key = auth._get_cache_key(normalized_phone, "rate_limit")
        
        logger.info(f"OTP cache key: {otp_key}")
        logger.info(f"Stored OTP in cache: {cache.get(otp_key)}")
        logger.info(f"Attempts in cache: {cache.get(attempts_key)}")
        logger.info(f"Rate limit in cache: {cache.get(rate_limit_key)}")
        
        # Try OTP verification
        try:
            result = auth.verify_otp(formatted_phone, otp)
            if result:
                logger.info("OTP verification successful!")
                
                # Get user type
                user_type, user_obj = auth.identify_user_type(formatted_phone)
                logger.info(f"User type: {user_type}")
                if user_obj:
                    if user_type.name == 'PATIENT':
                        logger.info(f"Patient: {user_obj.name}")
                    else:
                        logger.info(f"Staff: {user_obj.username}")
            else:
                logger.error("OTP verification failed!")
                # Check cache again after verification attempt
                logger.info(f"After verification - Stored OTP in cache: {cache.get(otp_key)}")
                logger.info(f"After verification - Attempts in cache: {cache.get(attempts_key)}")
            
            return result
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return False
    
    # Restore original SMS setting
    settings.USE_SMS = original_use_sms

if __name__ == "__main__":
    if len(sys.argv) > 2:
        phone_number = sys.argv[1]
        otp = sys.argv[2]
        verify_otp(phone_number, otp)
    else:
        logger.error("Please provide a phone number and OTP as arguments")
        logger.error("Usage: python verify_otp.py <phone_number> <otp>")