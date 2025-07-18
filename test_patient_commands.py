#!/usr/bin/env python3
"""
Test script to demonstrate patient commands for WhatsApp bot
"""

import requests
import json
import time

def send_whatsapp_message(phone_number, message_text):
    """Send a message to the WhatsApp webhook"""
    url = "http://localhost:8000/webhook/"
    
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
                        "id": f"wamid.test{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {
                            "body": message_text
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📱 Sent: '{message_text}' from {phone_number}")
        print(f"✅ Response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
        print("-" * 50)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def test_patient_commands():
    """Test patient commands for appointments, medications, and available slots"""
    
    # Use the patient phone number from our test database
    patient_phone = "+918767341919"  # This is the patient we created in our minimal DB
    
    print("🏥 Testing Patient Commands for WhatsApp Bot")
    print("=" * 60)
    
    # Test 1: Login
    print("🔐 Test 1: Patient Login")
    send_whatsapp_message(patient_phone, "login")
    time.sleep(2)
    
    # Test 2: Send OTP (simulated - in real scenario, patient would receive SMS)
    print("📱 Test 2: OTP Verification (using 123456 as test OTP)")
    send_whatsapp_message(patient_phone, "123456")
    time.sleep(2)
    
    # Test 3: View menu
    print("📋 Test 3: View Menu")
    send_whatsapp_message(patient_phone, "menu")
    time.sleep(2)
    
    # Test 4: Check appointments
    print("📅 Test 4: Check My Appointments")
    send_whatsapp_message(patient_phone, "appointments")
    time.sleep(2)
    
    # Test 5: Check medications
    print("💊 Test 5: Check My Medications")
    send_whatsapp_message(patient_phone, "medications")
    time.sleep(2)
    
    # Test 6: Check available slots
    print("🗓️ Test 6: Check Available Appointment Slots")
    send_whatsapp_message(patient_phone, "available slots")
    time.sleep(2)
    
    # Test 7: View medical records
    print("📋 Test 7: View Medical Records")
    send_whatsapp_message(patient_phone, "records")
    time.sleep(2)
    
    # Test 8: Book appointment
    print("📞 Test 8: Book Appointment")
    send_whatsapp_message(patient_phone, "book appointment")
    time.sleep(2)
    
    # Test 9: Help
    print("❓ Test 9: Get Help")
    send_whatsapp_message(patient_phone, "help")
    time.sleep(2)
    
    print("✅ All patient command tests completed!")
    print("\n📝 Note: Check the Django server logs to see the actual responses.")
    print("🔍 The bot should respond with formatted information for each command.")

if __name__ == "__main__":
    test_patient_commands()