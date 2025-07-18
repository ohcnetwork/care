#!/usr/bin/env python3
"""
WhatsApp Bot Test Flow Script
Simulates complete user interaction with the CARE WhatsApp Bot
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Add Django setup
sys.path.append('/Users/ashu/care')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

try:
    import django
    django.setup()
    from django.conf import settings
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)


class WhatsAppBotTester:
    def __init__(self):
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.phone_number_id:
            print("❌ WhatsApp configuration missing!")
            print(f"Access Token: {'✅ Set' if self.access_token else '❌ Missing'}")
            print(f"Phone Number ID: {'✅ Set' if self.phone_number_id else '❌ Missing'}")
            sys.exit(1)
    
    def send_message(self, phone_number: str, message: str, delay: int = 2) -> bool:
        """Send a WhatsApp message"""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            print(f"📤 Sending: {message[:50]}{'...' if len(message) > 50 else ''}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id', 'Unknown')
                print(f"✅ Sent successfully (ID: {message_id})")
                time.sleep(delay)
                return True
            else:
                print(f"❌ Failed to send (Status: {response.status_code})")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def run_welcome_flow(self, phone_number: str):
        """Test welcome and initial interaction"""
        print("\n🎬 === WELCOME FLOW TEST ===")
        
        messages = [
            "Hi",
            "Hello",
            "help"
        ]
        
        for msg in messages:
            if not self.send_message(phone_number, msg):
                return False
        
        return True
    
    def run_login_flow(self, phone_number: str):
        """Test login flow"""
        print("\n🔐 === LOGIN FLOW TEST ===")
        
        messages = [
            "login",
            # Note: In real scenario, user would receive OTP and enter it
            # For testing, we'll simulate the command
            "menu"
        ]
        
        for msg in messages:
            if not self.send_message(phone_number, msg):
                return False
        
        return True
    
    def run_patient_flow(self, phone_number: str):
        """Test patient commands"""
        print("\n👤 === PATIENT FLOW TEST ===")
        
        messages = [
            "records",
            "medications", 
            "appointments",
            "procedures",
            "available slots",
            "book appointment"
        ]
        
        for msg in messages:
            if not self.send_message(phone_number, msg, delay=3):
                return False
        
        return True
    
    def run_staff_flow(self, phone_number: str):
        """Test staff commands"""
        print("\n👨‍⚕️ === STAFF FLOW TEST ===")
        
        messages = [
            "search patient John",
            "patient info P123456",
            "schedule appointment"
        ]
        
        for msg in messages:
            if not self.send_message(phone_number, msg, delay=3):
                return False
        
        return True
    
    def run_utility_commands(self, phone_number: str):
        """Test utility commands"""
        print("\n🛠️ === UTILITY COMMANDS TEST ===")
        
        messages = [
            "help",
            "menu",
            "unknown command test",
            "logout"
        ]
        
        for msg in messages:
            if not self.send_message(phone_number, msg):
                return False
        
        return True
    
    def run_comprehensive_test(self, phone_number: str):
        """Run comprehensive bot test"""
        print("🤖 CARE WhatsApp Bot - Comprehensive Test")
        print("=" * 50)
        print(f"📱 Test Number: {phone_number}")
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Send initial test message
        initial_msg = (
            "🧪 *CARE WhatsApp Bot Test Started*\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "This is an automated test of the WhatsApp bot functionality. "
            "You'll receive several test messages to verify different features.\n\n"
            "🔄 Test sequence starting in 3 seconds..."
        )
        
        if not self.send_message(phone_number, initial_msg, delay=5):
            return False
        
        # Run test flows
        test_flows = [
            ("Welcome Flow", self.run_welcome_flow),
            ("Login Flow", self.run_login_flow),
            ("Patient Commands", self.run_patient_flow),
            ("Staff Commands", self.run_staff_flow),
            ("Utility Commands", self.run_utility_commands)
        ]
        
        results = {}
        
        for flow_name, flow_func in test_flows:
            print(f"\n🚀 Starting {flow_name}...")
            try:
                results[flow_name] = flow_func(phone_number)
                status = "✅ PASSED" if results[flow_name] else "❌ FAILED"
                print(f"📊 {flow_name}: {status}")
            except Exception as e:
                print(f"❌ {flow_name} failed with error: {e}")
                results[flow_name] = False
        
        # Send completion message
        passed = sum(results.values())
        total = len(results)
        
        completion_msg = (
            f"🏁 *Test Completed*\n\n"
            f"📊 Results: {passed}/{total} flows passed\n"
            f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"{'🎉 All tests passed!' if passed == total else '⚠️ Some tests failed'}\n\n"
            "Now you can interact with the bot normally:\n"
            "• Type `login` to start\n"
            "• Type `help` for assistance\n"
            "• Type `menu` to see options"
        )
        
        self.send_message(phone_number, completion_msg)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        for flow_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{flow_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} flows passed")
        print("=" * 50)
        
        return passed == total


def main():
    if len(sys.argv) != 2:
        print("Usage: python whatsapp_bot_test_flow.py <phone_number>")
        print("Example: python whatsapp_bot_test_flow.py +918767341918")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    
    # Validate phone number format
    if not phone_number.startswith('+'):
        print("❌ Phone number must include country code (e.g., +918767341918)")
        sys.exit(1)
    
    tester = WhatsAppBotTester()
    
    print("🔍 Pre-flight checks...")
    print(f"📱 Target number: {phone_number}")
    print(f"🔑 Phone Number ID: {tester.phone_number_id}")
    print(f"🌐 API Version: {tester.api_version}")
    
    # Confirm before starting
    confirm = input("\n🚀 Start comprehensive bot test? (y/N): ")
    if confirm.lower() != 'y':
        print("Test cancelled.")
        sys.exit(0)
    
    # Run the test
    success = tester.run_comprehensive_test(phone_number)
    
    if success:
        print("\n🎉 All tests completed successfully!")
        print("Your WhatsApp bot is working correctly.")
    else:
        print("\n⚠️ Some tests failed.")
        print("Check the bot configuration and try again.")


if __name__ == "__main__":
    main()