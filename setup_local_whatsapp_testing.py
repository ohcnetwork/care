#!/usr/bin/env python3
"""
Setup script for local WhatsApp testing with ngrok
"""

import subprocess
import sys
import time
import requests
import json
from urllib.parse import urljoin

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ngrok is installed:", result.stdout.strip())
            return True
        else:
            print("❌ ngrok is not installed or not working")
            return False
    except FileNotFoundError:
        print("❌ ngrok is not installed")
        return False

def start_ngrok():
    """Start ngrok tunnel for port 8000"""
    print("\n🚀 Starting ngrok tunnel for port 8000...")
    print("📝 Note: Keep this terminal open while testing")
    
    try:
        # Start ngrok in background
        process = subprocess.Popen(['ngrok', 'http', '8000'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Wait a bit for ngrok to start
        time.sleep(3)
        
        # Get the public URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()
            
            if tunnels['tunnels']:
                public_url = tunnels['tunnels'][0]['public_url']
                webhook_url = f"{public_url}/api/care_whatsapp_bot/webhook/"
                
                print(f"✅ ngrok tunnel started successfully!")
                print(f"🌐 Public URL: {public_url}")
                print(f"🔗 Webhook URL: {webhook_url}")
                
                return webhook_url, process
            else:
                print("❌ No tunnels found")
                return None, process
                
        except Exception as e:
            print(f"❌ Error getting tunnel info: {e}")
            return None, process
            
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        return None, None

def update_webhook_url(webhook_url):
    """Instructions to update webhook URL in Meta Developer Console"""
    print(f"\n📋 Next Steps:")
    print(f"1. Go to Meta Developer Console: https://developers.facebook.com/")
    print(f"2. Navigate to your WhatsApp Business app")
    print(f"3. Go to WhatsApp > Configuration")
    print(f"4. Update the webhook URL to: {webhook_url}")
    print(f"5. Verify token: GSoC2025CareBot")
    print(f"6. Subscribe to 'messages' field")
    print(f"\n🧪 Test by sending messages to your WhatsApp Business number!")

def test_local_webhook(webhook_url):
    """Test the local webhook"""
    print(f"\n🧪 Testing local webhook...")
    
    test_payload = {
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
                        "from": "918767341918",
                        "id": "test_msg_hi",
                        "timestamp": str(int(time.time())),
                        "text": {
                            "body": "hi"
                        },
                        "type": "text"
                    }]
                }
            }]
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        if response.status_code == 200:
            print("✅ Webhook test successful!")
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Webhook test error: {e}")

def main():
    print("🏥 CARE WhatsApp Bot - Local Testing Setup")
    print("=" * 50)
    
    # Check if Django server is running
    try:
        response = requests.get('http://localhost:8000/ping/', timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running on port 8000")
        else:
            print("❌ Django server is not responding properly")
            return
    except:
        print("❌ Django server is not running on port 8000")
        print("💡 Please start the server with: python manage.py runserver 8000")
        return
    
    # Check ngrok
    if not check_ngrok_installed():
        print("\n📦 To install ngrok:")
        print("1. Visit: https://ngrok.com/download")
        print("2. Download and install ngrok")
        print("3. Sign up for a free account")
        print("4. Run: ngrok authtoken YOUR_TOKEN")
        return
    
    # Start ngrok
    webhook_url, process = start_ngrok()
    
    if webhook_url:
        # Test webhook
        test_local_webhook(webhook_url)
        
        # Show instructions
        update_webhook_url(webhook_url)
        
        print(f"\n⚠️  Important:")
        print(f"• Keep this script running while testing")
        print(f"• The ngrok URL changes each time you restart")
        print(f"• Update the webhook URL in Meta Console each time")
        print(f"\n🛑 Press Ctrl+C to stop ngrok tunnel")
        
        try:
            # Keep running
            process.wait()
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping ngrok tunnel...")
            process.terminate()
            print(f"✅ Tunnel stopped")
    else:
        print("❌ Failed to start ngrok tunnel")

if __name__ == "__main__":
    main()