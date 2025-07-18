import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache

from care_whatsapp_bot.authentication import WhatsAppAuthenticator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test SMS functionality by sending a verification code to a phone number'

    def add_arguments(self, parser):
        parser.add_argument('phone_number', type=str, help='Phone number to send the verification code to')

    def handle(self, *args, **options):
        # Temporarily enable SMS functionality
        original_use_sms = settings.USE_SMS
        settings.USE_SMS = True

        try:
            phone_number = options['phone_number']
            
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
            
            self.stdout.write(f"Using phone number: {phone_number}")
            
            auth = WhatsAppAuthenticator()
            
            # Clear any existing rate limits
            normalized_phone = auth._normalize_phone_number(phone_number)
            rate_limit_key = auth._get_cache_key(normalized_phone, "rate_limit")
            cache.delete(rate_limit_key)
            
            self.stdout.write(f"Generating OTP for {phone_number}")
            self.stdout.write(f"USE_SMS setting: {settings.USE_SMS}")
            
            otp = auth.generate_otp(phone_number)
            
            if otp:
                self.stdout.write(self.style.SUCCESS(f"OTP generated successfully: {otp}"))
                self.stdout.write(f"Normalized phone number: {normalized_phone}")
            else:
                self.stdout.write(self.style.ERROR("Failed to generate OTP"))
        
        finally:
            # Restore original SMS setting
            settings.USE_SMS = original_use_sms