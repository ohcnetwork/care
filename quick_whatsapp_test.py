#!/usr/bin/env python3
"""
🚀 Quick WhatsApp Test - Send Message to Your Phone
===================================================

This script helps you send a test message to your WhatsApp to verify everything works!
"""

import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ashu/care')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DJANGO_READ_DOT_ENV_FILE', 'True')

# Setup Django
django.setup()

from django.conf import settings

def send_test_message(phone_number):
    """Send a test message to the specified phone number"""
    
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    
    if not access_token or not phone_number_id:
        print("❌ WhatsApp configuration missing!")
        return False
    
    # Clean phone number (remove spaces, dashes, etc.)
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    if not clean_phone.startswith('91'):  # Add India country code if missing
        clean_phone = '91' + clean_phone
    
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    message = """🤖 *CARE WhatsApp Bot Test Message*

Hey! 👋 This is a test message from your CARE WhatsApp Bot!

If you're receiving this, it means:
✅ Your phone number is in the allowed list
✅ The bot configuration is working
✅ You can now test the bot commands!

*Try these commands:*
• Type "hi" for welcome message
• Type "help" for all commands
• Type "register" to create account
• Type "login" to access your account

🏥 Ready to manage your healthcare via WhatsApp!

_This is an automated test message._"""
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': clean_phone,
        'type': 'text',
        'text': {'body': message}
    }
    
    try:
        print(f"📱 Sending test message to +{clean_phone}...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'unknown')
            print(f"✅ Message sent successfully!")
            print(f"📧 Message ID: {message_id}")
            print(f"📱 Check your WhatsApp for the test message!")
            return True
        else:
            print(f"❌ Failed to send message:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            # Common error explanations
            if response.status_code == 400:
                error_data = response.json()
                error_code = error_data.get('error', {}).get('code', 0)
                
                if error_code == 131026:
                    print("\n💡 This error means your phone number is not in the allowed list!")
                    print("   Go to Meta Developer Console and add your number.")
                elif error_code == 131047:
                    print("\n💡 This error means the recipient cannot be reached.")
                    print("   Make sure the phone number is correct and has WhatsApp.")
                else:
                    print(f"\n💡 Error code: {error_code}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def main():
    """Main function"""
    print("🚀 CARE WhatsApp Bot - Quick Test")
    print("=" * 50)
    
    # Get phone number from user
    phone_number = input("📱 Enter your phone number (with country code, e.g., +918767341918): ").strip()
    
    if not phone_number:
        print("❌ Phone number is required!")
        return
    
    # Remove + if present
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    print(f"\n🔄 Testing WhatsApp bot with number: +{phone_number}")
    
    success = send_test_message(phone_number)
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("\nNext steps:")
        print("1. Check your WhatsApp for the test message")
        print("2. Reply with 'hi' to start interacting with the bot")
        print("3. Try commands like 'help', 'register', 'login'")
        print("4. Use patient commands after logging in")
    else:
        print("\n❌ Test failed!")
        print("\nTroubleshooting:")
        print("1. Make sure your phone number is added to the allowed list in Meta Developer Console")
        print("2. Verify your WhatsApp Business API configuration")
        print("3. Check if the Django server is running")
        print("4. Ensure your phone number has WhatsApp installed")

if __name__ == "__main__":
    main()