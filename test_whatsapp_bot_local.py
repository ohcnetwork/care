#!/usr/bin/env python3
"""
Test script to verify WhatsApp bot functionality locally
"""

import requests
import json
import time

def test_whatsapp_command(phone_number, command, description=""):
    """Test a WhatsApp command via local webhook"""
    url = "http://localhost:8000/api/care_whatsapp_bot/webhook/"
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550559999",
                        "phone_number_id": "651347521403933"
                    },
                    "messages": [{
                        "from": phone_number,
                        "id": f"test_msg_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {
                            "body": command
                        },
                        "type": "text"
                    }]
                }
            }]
        }]
    }
    
    print(f"\n🧪 Testing: {command}")
    if description:
        print(f"📝 {description}")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Command processed successfully (200)")
        else:
            print(f"❌ Command failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1)  # Small delay between requests

def main():
    print("🏥 CARE WhatsApp Bot - Local Testing")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/ping/', timeout=5)
        if response.status_code != 200:
            print("❌ Django server is not responding properly")
            return
    except:
        print("❌ Django server is not running on port 8000")
        print("💡 Please start the server with: python manage.py runserver 8000")
        return
    
    print("✅ Django server is running")
    
    # Test phone number
    phone_number = "918767341918"
    
    # Test basic commands
    print(f"\n📱 Testing with phone number: {phone_number}")
    
    test_commands = [
        ("hi", "Basic greeting"),
        ("register", "User registration"),
        ("login", "User login"),
        ("menu", "Show menu"),
        ("help", "Show help"),
        ("appointments", "View appointments"),
        ("medications", "View medications"),
        ("available slots", "Check available slots"),
        ("records", "View medical records"),
        ("logout", "User logout"),
    ]
    
    for command, description in test_commands:
        test_whatsapp_command(phone_number, command, description)
    
    print(f"\n✅ Testing completed!")
    print(f"📋 Check the Django server logs for detailed responses")
    print(f"💡 The bot is processing commands but can't send responses to WhatsApp")
    print(f"   because it's running locally. Use ngrok for real WhatsApp testing.")

if __name__ == "__main__":
    main()