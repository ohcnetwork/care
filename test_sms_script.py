#!/usr/bin/env python
import os
import sys
import django
import logging

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
logger.info(f"SNS_ROLE_BASED_MODE: {getattr(settings, 'SNS_ROLE_BASED_MODE', None)}")
logger.info(f"SNS_REGION: {getattr(settings, 'SNS_REGION', None)}")
logger.info(f"SNS_ACCESS_KEY exists: {bool(getattr(settings, 'SNS_ACCESS_KEY', None))}")
logger.info(f"SNS_SECRET_KEY exists: {bool(getattr(settings, 'SNS_SECRET_KEY', None))}")

from care_whatsapp_bot.authentication import WhatsAppAuthenticator
from care.utils.sms.send_sms import send_sms

def test_otp_generation(phone_number):
    # Format phone number correctly for Indian mobile
    if not phone_number.startswith('+91'):
        if phone_number.startswith('+'):
            # Remove the + and add +91
            phone_number = '+91' + phone_number[1:]
        elif phone_number.startswith('91'):
            # Add the +
            phone_number = '+' + phone_number
        else:
            # Add +91
            phone_number = '+91' + phone_number
    
    logger.info(f"Using phone number: {phone_number}")
    
    auth = WhatsAppAuthenticator()
    
    # Clear any existing rate limits
    normalized_phone = auth._normalize_phone_number(phone_number)
    rate_limit_key = auth._get_cache_key(normalized_phone, "rate_limit")
    cache.delete(rate_limit_key)
    
    logger.info(f"Generating OTP for {phone_number}")
    logger.info(f"USE_SMS setting: {settings.USE_SMS}")
    
    # Try direct SMS sending
    try:
        logger.info("Attempting to send SMS directly...")
        message = "This is a test message from CARE WhatsApp Bot."
        result = send_sms(phone_number, message)
        logger.info(f"Direct SMS send result: {result}")
    except Exception as e:
        logger.error(f"Error sending SMS directly: {e}")
    
    # Try OTP generation
    try:
        otp = auth.generate_otp(phone_number)
        
        if otp:
            logger.info(f"OTP generated successfully: {otp}")
            logger.info(f"Normalized phone number: {normalized_phone}")
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