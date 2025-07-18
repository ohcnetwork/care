#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

# Now we can import Django models
from django.conf import settings
from django.core.cache import cache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporarily override settings
settings.USE_SMS = True

from care_whatsapp_bot.authentication import WhatsAppAuthenticator

def test_otp_generation(phone_number):
    auth = WhatsAppAuthenticator()
    
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
    
    # Clear any existing rate limits
    rate_limit_key = auth._get_cache_key(auth._normalize_phone_number(phone_number), "rate_limit")
    cache.delete(rate_limit_key)
    
    logger.info(f"Generating OTP for {phone_number}")
    logger.info(f"USE_SMS setting: {settings.USE_SMS}")
    otp = auth.generate_otp(phone_number)
    
    if otp:
        logger.info(f"OTP generated successfully: {otp}")
        logger.info(f"Normalized phone number: {auth._normalize_phone_number(phone_number)}")
    else:
        logger.error("Failed to generate OTP")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
        test_otp_generation(phone_number)
    else:
        logger.error("Please provide a phone number as argument")