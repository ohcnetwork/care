from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Send a test WhatsApp message'

    def add_arguments(self, parser):
        parser.add_argument(
            'phone_number',
            type=str,
            help='Phone number to send message to (with country code, e.g., +918767341918)'
        )
        parser.add_argument(
            '--message',
            type=str,
            default=None,
            help='Custom message to send (optional)'
        )

    def handle(self, *args, **options):
        phone_number = options['phone_number']
        custom_message = options.get('message')
        
        if custom_message:
            message = custom_message
        else:
            message = f"🤖 Test message from CARE WhatsApp Bot\n\n" \
                     f"Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" \
                     f"✅ Bot is working correctly!\n" \
                     f"🏥 CARE - Open Healthcare Network"
        
        self.stdout.write("📱 Sending WhatsApp Test Message")
        self.stdout.write("================================\n")
        
        access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        
        if not access_token or not phone_number_id:
            self.stdout.write(
                self.style.ERROR("❌ WhatsApp configuration missing")
            )
            self.stdout.write(f"Access Token: {'✅ Set' if access_token else '❌ Missing'}")
            self.stdout.write(f"Phone Number ID: {'✅ Set' if phone_number_id else '❌ Missing'}")
            return
        
        self.stdout.write(f"📞 To: {phone_number}")
        self.stdout.write(f"💬 Message: {message[:100]}{'...' if len(message) > 100 else ''}")
        self.stdout.write(f"🔑 Phone Number ID: {phone_number_id}\n")
        
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            self.stdout.write("🚀 Sending message...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.stdout.write(
                    self.style.SUCCESS("✅ Message sent successfully!")
                )
                
                # Extract message ID for reference
                if 'messages' in result and result['messages']:
                    message_id = result['messages'][0].get('id', 'Unknown')
                    self.stdout.write(f"📋 Message ID: {message_id}")
                
                self.stdout.write("\n🎉 Check your WhatsApp to see the message!")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to send message (Status: {response.status_code})")
                )
                self.stdout.write(f"📄 Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Network error: {e}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Unexpected error: {e}")
            )