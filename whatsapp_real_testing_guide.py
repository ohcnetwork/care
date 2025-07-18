#!/usr/bin/env python3
"""
🤖 CARE WhatsApp Bot - Real WhatsApp Testing Guide
==================================================

This guide will help you test the bot on your actual WhatsApp!

Prerequisites:
1. WhatsApp Business API account set up
2. Your phone number added to the allowed list in Meta Developer Console
3. Django server running with proper configuration
"""

import os
import sys
import django
import requests
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ashu/care')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DJANGO_READ_DOT_ENV_FILE', 'True')

# Setup Django
django.setup()

from django.conf import settings

def check_whatsapp_config():
    """Check if WhatsApp configuration is properly set up"""
    print("🔧 Checking WhatsApp Configuration...")
    print("=" * 50)
    
    config_items = [
        ('WHATSAPP_ACCESS_TOKEN', getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')),
        ('WHATSAPP_PHONE_NUMBER_ID', getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')),
        ('WHATSAPP_WEBHOOK_VERIFY_TOKEN', getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', '')),
        ('WHATSAPP_VERIFY_TOKEN', getattr(settings, 'WHATSAPP_VERIFY_TOKEN', '')),
        ('WHATSAPP_WEBHOOK_URL', getattr(settings, 'WHATSAPP_WEBHOOK_URL', '')),
    ]
    
    all_configured = True
    for name, value in config_items:
        if value:
            print(f"✅ {name}: {'*' * 20}...{value[-10:]}")
        else:
            print(f"❌ {name}: Not configured")
            all_configured = False
    
    return all_configured

def test_whatsapp_api():
    """Test WhatsApp API connectivity"""
    print("\n📡 Testing WhatsApp API Connectivity...")
    print("=" * 50)
    
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    
    if not access_token or not phone_number_id:
        print("❌ Missing access token or phone number ID")
        return False
    
    try:
        url = f"https://graph.facebook.com/v23.0/{phone_number_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connected to WhatsApp Business Phone: {data.get('display_phone_number', 'Unknown')}")
            print(f"✅ Phone Number ID: {phone_number_id}")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def show_testing_instructions():
    """Show step-by-step testing instructions"""
    print("\n📱 How to Test on Your Real WhatsApp")
    print("=" * 50)
    
    print("""
🔥 IMPORTANT: Your phone number must be added to the allowed list in Meta Developer Console!

Step 1: Add Your Phone Number to Allowed List
---------------------------------------------
1. Go to Meta Developer Console: https://developers.facebook.com/
2. Select your WhatsApp Business app
3. Go to WhatsApp > Getting Started
4. In the "Send and receive messages" section, add your phone number
5. Verify your phone number with the OTP sent

Step 2: Test the Bot Commands
-----------------------------
Once your number is added, send these messages to your WhatsApp Business number:

🚀 BASIC COMMANDS:
• "hi" or "hello" - Get welcome message
• "help" - See all available commands  
• "menu" - Show main menu

🔐 REGISTRATION & LOGIN:
• "register" - Start registration process
• "login" - Login with your phone number

👤 PATIENT COMMANDS (after login):
• "appointments" - View your appointments
• "medications" - See your medications
• "available slots" - Check available appointment slots
• "records" - View your medical records
• "procedures" - See your procedures
• "book appointment" - Book a new appointment

🏥 STAFF COMMANDS (for hospital staff):
• "patients" - View patient list
• "schedule" - Check schedule
• "notifications" - View notifications

Step 3: Expected Flow
--------------------
1. Send "hi" → Bot responds with welcome message
2. Send "register" → Bot asks for details
3. Follow registration process
4. Send "login" → Bot asks for phone number
5. Enter OTP when received
6. Send "menu" → See available options
7. Try patient commands like "appointments"

Step 4: Troubleshooting
----------------------
If messages don't work:
• Check if your number is in the allowed list
• Verify the Django server is running
• Check server logs for errors
• Ensure webhook URL is accessible
""")

def show_webhook_setup():
    """Show webhook setup instructions"""
    print("\n🔗 Webhook Setup Instructions")
    print("=" * 50)
    
    webhook_url = getattr(settings, 'WHATSAPP_WEBHOOK_URL', '')
    verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', '')
    
    print(f"""
Your webhook configuration:
• Webhook URL: {webhook_url}
• Verify Token: {verify_token}

To set up the webhook in Meta Developer Console:
1. Go to WhatsApp > Configuration
2. Set Webhook URL: {webhook_url}
3. Set Verify Token: {verify_token}
4. Subscribe to 'messages' events
5. Click 'Verify and Save'

The webhook should be accessible at:
{webhook_url}
""")

def show_sample_conversation():
    """Show a sample conversation flow"""
    print("\n💬 Sample Conversation Flow")
    print("=" * 50)
    
    conversation = [
        ("You", "hi"),
        ("Bot", "👋 Welcome to the Care WhatsApp Bot! I'm here to help you manage your healthcare needs..."),
        ("You", "register"),
        ("Bot", "🏥 Welcome to CARE! Let's get you registered..."),
        ("You", "John Doe"),
        ("Bot", "Great! Now please provide your date of birth (DD/MM/YYYY):"),
        ("You", "01/01/1990"),
        ("Bot", "Perfect! Please provide your gender (Male/Female/Other):"),
        ("You", "Male"),
        ("Bot", "✅ Registration successful! You can now login..."),
        ("You", "login"),
        ("Bot", "Please provide your phone number:"),
        ("You", "+918767341918"),
        ("Bot", "📱 OTP sent! Please enter the 6-digit code:"),
        ("You", "123456"),
        ("Bot", "✅ Login successful! Welcome John Doe!"),
        ("You", "menu"),
        ("Bot", "🏥 *CARE WhatsApp Bot*\n\nAvailable commands:\n• appointments\n• medications\n• available slots..."),
        ("You", "appointments"),
        ("Bot", "📅 *Your Appointments*\n\nNo upcoming appointments found..."),
    ]
    
    for sender, message in conversation:
        if sender == "You":
            print(f"📱 {sender}: {message}")
        else:
            print(f"🤖 {sender}: {message[:80]}...")
        print()

def main():
    """Main function to run the testing guide"""
    print("🤖 CARE WhatsApp Bot - Real Testing Guide")
    print("=" * 60)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check configuration
    config_ok = check_whatsapp_config()
    
    if not config_ok:
        print("\n❌ Configuration incomplete! Please check your .env file.")
        return
    
    # Test API connectivity
    api_ok = test_whatsapp_api()
    
    if not api_ok:
        print("\n❌ API connectivity failed! Please check your tokens.")
        return
    
    # Show instructions
    show_testing_instructions()
    show_webhook_setup()
    show_sample_conversation()
    
    print("\n🎉 Ready to Test!")
    print("=" * 50)
    print("Your WhatsApp bot is configured and ready!")
    print("Add your phone number to the allowed list and start testing! 🚀")

if __name__ == "__main__":
    main()