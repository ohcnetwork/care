#!/usr/bin/env python
import os
import sys
import django
import logging
import json
import re
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

# Import AWS SNS settings
logger.info(f"Original USE_SMS setting: {original_use_sms}")
logger.info(f"Current USE_SMS setting: {settings.USE_SMS}")

from care_whatsapp_bot.authentication import WhatsAppAuthenticator

# Mock the send_sms function to avoid actual SMS sending
def mock_send_sms(phone_numbers, message, many=False):
    if not many:
        phone_numbers = [phone_numbers]
    
    for phone in phone_numbers:
        logger.info(f"MOCK SMS: Would send '{message}' to {phone}")
    
    return True

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

def test_otp_generation(phone_number):
    # Format phone number correctly for Indian mobile
    formatted_phone = format_indian_mobile(phone_number)
    if not formatted_phone:
        logger.error(f"Could not format phone number: {phone_number}")
        return
    
    logger.info(f"Using phone number: {formatted_phone}")
    
    # Patch both the send_sms function and the mobile_validator
    with patch('care.utils.sms.send_sms.send_sms', mock_send_sms), \
         patch('care.utils.models.validators.mobile_validator', mock_mobile_validator):
        
        auth = WhatsAppAuthenticator()
        
        # Clear any existing rate limits and OTPs
        normalized_phone = auth._normalize_phone_number(formatted_phone)
        rate_limit_key = auth._get_cache_key(normalized_phone, "rate_limit")
        otp_key = auth._get_cache_key(normalized_phone, "otp")
        attempts_key = auth._get_cache_key(normalized_phone, "attempts")
        
        # Clear all related cache keys
        cache.delete(rate_limit_key)
        cache.delete(otp_key)
        cache.delete(attempts_key)
        
        logger.info(f"Generating OTP for {formatted_phone}")
        logger.info(f"Normalized phone by WhatsAppAuthenticator: {normalized_phone}")
        
        # Try OTP generation
        try:
            otp = auth.generate_otp(formatted_phone)
            
            if otp:
                logger.info(f"OTP generated successfully: {otp}")
                
                # Debug cache keys
                logger.info(f"OTP cache key: {otp_key}")
                logger.info(f"Stored OTP in cache: {cache.get(otp_key)}")
                
                # Store OTP in a file for easy access
                with open('last_otp.json', 'w') as f:
                    json.dump({
                        'phone_number': formatted_phone,
                        'normalized_phone': normalized_phone,
                        'otp': otp,
                        'timestamp': str(django.utils.timezone.now())
                    }, f, indent=2)
                logger.info(f"OTP saved to last_otp.json")
                
                # Also print verification instructions
                logger.info("\nTo verify this OTP, you can run:")
                logger.info(f"python verify_otp.py {phone_number} {otp}")
            else:
                logger.error("Failed to generate OTP")
        except Exception as e:
            logger.error(f"Error generating OTP: {e}")

    # Restore original SMS setting
    settings.USE_SMS = original_use_sms

if __name__ == "__main__":
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
        test_otp_generation(phone_number)
    else:
        logger.error("Please provide a phone number as argument")