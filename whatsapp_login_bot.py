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
from care_whatsapp_bot.command_types import UserType

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

def generate_otp(phone_number):
    """Generate OTP for the given phone number"""
    # Format phone number correctly for Indian mobile
    formatted_phone = format_indian_mobile(phone_number)
    if not formatted_phone:
        logger.error(f"Could not format phone number: {phone_number}")
        return None
    
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
        
        # Try OTP generation
        try:
            otp = auth.generate_otp(formatted_phone)
            
            if otp:
                logger.info(f"OTP generated successfully: {otp}")
                
                # Store OTP in a file for easy access
                with open('last_otp.json', 'w') as f:
                    json.dump({
                        'phone_number': formatted_phone,
                        'normalized_phone': normalized_phone,
                        'otp': otp,
                        'timestamp': str(django.utils.timezone.now())
                    }, f, indent=2)
                logger.info(f"OTP saved to last_otp.json")
                
                return otp
            else:
                logger.error("Failed to generate OTP")
                return None
        except Exception as e:
            logger.error(f"Error generating OTP: {e}")
            return None

def verify_otp(phone_number, otp):
    """Verify OTP for the given phone number"""
    # Format phone number correctly for Indian mobile
    formatted_phone = format_indian_mobile(phone_number)
    if not formatted_phone:
        logger.error(f"Could not format phone number: {phone_number}")
        return False
    
    logger.info(f"Using phone number: {formatted_phone}")
    
    # Patch the mobile_validator
    with patch('care.utils.models.validators.mobile_validator', mock_mobile_validator):
        auth = WhatsAppAuthenticator()
        
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
                        return f"Welcome, {user_obj.name}! You are now logged in as a patient."
                    else:
                        logger.info(f"Staff: {user_obj.username}")
                        return f"Welcome, {user_obj.username}! You are now logged in as a staff member."
                return "You are now logged in!"
            else:
                logger.error("OTP verification failed!")
                return "Invalid OTP. Please try again."
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return "Error verifying OTP. Please try again."

def search_patient(query):
    """Search for patients by name, phone number, or ID"""
    try:
        from care.emr.models.patient import Patient
        from django.db.models import Q
        
        if not query or len(query) < 2:
            return "❓ Please provide a search term (minimum 2 characters).\nExample: `search patient John Doe`"
        
        # Search for patients matching the query
        patients = Patient.objects.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(external_id__icontains=query)
        )[:10]  # Limit to 10 results
        
        if not patients:
            return f"🔍 No patients found matching '{query}'.\nTry searching with a different term."
        
        results_text = f"🔍 *Search Results for '{query}'*\n\n"
        
        for i, patient in enumerate(patients, 1):
            results_text += f"*{i}. {patient.name}*\n"
            results_text += f"   ID: {patient.external_id}\n"
            
            if patient.date_of_birth:
                results_text += f"   Age: {patient.get_age()}\n"
            
            if patient.gender:
                results_text += f"   Gender: {patient.gender}\n"
            
            # Mask phone number for privacy
            if patient.phone_number:
                masked_phone = patient.phone_number[-4:].rjust(len(patient.phone_number), '*')
                results_text += f"   Phone: {masked_phone}\n"
            
            results_text += "\n"
        
        results_text += "\n💡 Use `patient info <ID>` for details."
        
        return results_text
    
    except Exception as e:
        logger.error(f"Error searching patients: {e}")
        return "Sorry, there was an error processing your search request."

def process_message(phone_number, message):
    """Process incoming WhatsApp message"""
    message = message.strip()
    message_lower = message.lower()
    
    if message_lower == 'login':
        # Generate OTP for login
        otp = generate_otp(phone_number)
        if otp:
            return f"Your OTP for login is: {otp}. Please enter this OTP to complete login."
        else:
            return "Failed to generate OTP. Please try again later."
    
    # Check if message is a 6-digit OTP
    elif message.isdigit() and len(message) == 6:
        # Verify OTP
        result = verify_otp(phone_number, message)
        return result
    
    # Handle patient search command
    elif message_lower.startswith('search patient ') or message_lower.startswith('patient search '):
        # Extract search query
        if message_lower.startswith('search patient '):
            query = message[14:].strip()
        else:  # starts with 'patient search '
            query = message[15:].strip()
        
        return search_patient(query)
    
    # Help command
    elif message_lower == 'help':
        return """🏥 *CARE WhatsApp Bot Help*\n\n*Available Commands:*\n\n- `login` - Authenticate with OTP\n- `search patient <name>` - Search for patients\n- `patient info <ID>` - Get patient details\n- `help` - Show this help message"""
    
    else:
        return "Welcome to CARE WhatsApp Bot! Type 'login' to authenticate or 'help' for available commands."

def simulate_conversation():
    """Simulate a WhatsApp conversation"""
    phone_number = input("Enter your phone number (with country code): ")
    
    print("\nWelcome to CARE WhatsApp Bot Simulator!")
    print("Type 'exit' to quit the simulation.\n")
    
    while True:
        user_message = input("You: ")
        if user_message.lower() == 'exit':
            break
        
        bot_response = process_message(phone_number, user_message)
        print(f"Bot: {bot_response}\n")

if __name__ == "__main__":
    try:
        simulate_conversation()
    finally:
        # Restore original SMS setting
        settings.USE_SMS = original_use_sms