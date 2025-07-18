import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.urls import reverse
import json


class Command(BaseCommand):
    help = 'Set up WhatsApp webhook and verify configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--webhook-url',
            type=str,
            help='Full webhook URL'
        )
        parser.add_argument(
            '--verify-token',
            type=str,
            help='Webhook verify token'
        )
        parser.add_argument(
            '--access-token',
            type=str,
            help='WhatsApp Business API access token'
        )
        parser.add_argument(
            '--phone-number-id',
            type=str,
            help='WhatsApp Business phone number ID'
        )
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Only verify current webhook configuration'
        )
        parser.add_argument(
            '--test-message',
            type=str,
            help='Send a test message to this phone number'
        )
    
    def handle(self, *args, **options):
        webhook_url = options.get('webhook_url') or getattr(settings, 'WHATSAPP_WEBHOOK_URL', None)
        verify_token = options.get('verify_token') or getattr(settings, 'WHATSAPP_VERIFY_TOKEN', None)
        access_token = options.get('access_token') or getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        phone_number_id = options.get('phone_number_id') or getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        
        if not all([webhook_url, verify_token, access_token, phone_number_id]):
            raise CommandError(
                'Missing required configuration. Please provide:\n'
                '- webhook_url (or WHATSAPP_WEBHOOK_URL in settings)\n'
                '- verify_token (or WHATSAPP_VERIFY_TOKEN in settings)\n'
                '- access_token (or WHATSAPP_ACCESS_TOKEN in settings)\n'
                '- phone_number_id (or WHATSAPP_PHONE_NUMBER_ID in settings)'
            )
        
        self.stdout.write('WhatsApp Webhook Setup')
        self.stdout.write('=' * 50)
        
        if options.get('verify_only'):
            self.verify_webhook_config(webhook_url, verify_token, access_token, phone_number_id)
            return
        
        self.setup_webhook(webhook_url, verify_token, access_token, phone_number_id)
        
        test_phone = options.get('test_message')
        if test_phone:
            self.send_test_message(access_token, phone_number_id, test_phone)
    
    def setup_webhook(self, webhook_url, verify_token, access_token, phone_number_id):
        """Set up WhatsApp webhook"""
        self.stdout.write('Setting up WhatsApp webhook...')
        
        url = f'https://graph.facebook.com/v18.0/{phone_number_id}/webhooks'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'webhook_url': webhook_url,
            'verify_token': verify_token,
            'subscribed_fields': [
                'messages',
                'message_deliveries',
                'message_reads',
                'message_echoes'
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                self.stdout.write(
                    self.style.SUCCESS('✓ Webhook configured successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Webhook setup failed: {result}')
                )
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error setting up webhook: {e}')
            )
        
        self.verify_webhook_config(webhook_url, verify_token, access_token, phone_number_id)
    
    def verify_webhook_config(self, webhook_url, verify_token, access_token, phone_number_id):
        """Verify webhook configuration"""
        self.stdout.write('\nVerifying webhook configuration...')
        
        self.stdout.write(f'Webhook URL: {webhook_url}')
        
        try:
            verify_url = f'{webhook_url}?hub.mode=subscribe&hub.challenge=test_challenge&hub.verify_token={verify_token}'
            response = requests.get(verify_url, timeout=10)
            
            if response.status_code == 200 and response.text == 'test_challenge':
                self.stdout.write(
                    self.style.SUCCESS('✓ Webhook verification endpoint working')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Webhook verification failed. '
                        f'Status: {response.status_code}, '
                        f'Response: {response.text}'
                    )
                )
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Cannot reach webhook URL: {e}')
            )
        
        self.stdout.write('\nTesting WhatsApp API connectivity...')
        
        url = f'https://graph.facebook.com/v18.0/{phone_number_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            phone_info = response.json()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Connected to WhatsApp Business phone: '
                    f'{phone_info.get("display_phone_number", "Unknown")}'
                )
            )
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ WhatsApp API connection failed: {e}')
            )
    
    def send_test_message(self, access_token, phone_number_id, test_phone):
        """Send a test message"""
        self.stdout.write(f'\nSending test message to {test_phone}...')
        
        url = f'https://graph.facebook.com/v18.0/{phone_number_id}/messages'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': test_phone,
            'type': 'text',
            'text': {
                'body': '🏥 Hello from CARE WhatsApp Bot!\n\nTest message to verify integration.\n\nType "help" for commands.'
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('messages'):
                message_id = result['messages'][0]['id']
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Test message sent successfully! '
                        f'Message ID: {message_id}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to send test message: {result}')
                )
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error sending test message: {e}')
            )
    
    def print_configuration_help(self):
        """Print configuration help"""
        self.stdout.write('\nConfiguration Help:')
        self.stdout.write('=' * 50)
        self.stdout.write(
            'Add the following to your Django settings:\n\n'
            'WHATSAPP_ACCESS_TOKEN = "your_access_token"\n'
            'WHATSAPP_PHONE_NUMBER_ID = "your_phone_number_id"\n'
            'WHATSAPP_APP_SECRET = "your_app_secret"\n'
            'WHATSAPP_VERIFY_TOKEN = "your_verify_token"\n'
            'WHATSAPP_WEBHOOK_URL = "https://your-domain.com/whatsapp/webhook/"\n\n'
            'For development, you can use ngrok to expose your local server:\n'
            '1. Install ngrok: https://ngrok.com/\n'
            '2. Run: ngrok http 8000\n'
            '3. Use the HTTPS URL provided by ngrok\n'
        )