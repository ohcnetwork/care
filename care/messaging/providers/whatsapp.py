import requests
from django.conf import settings
from care.messaging.providers.base import BaseMessagingProvider


class WhatsAppProvider(BaseMessagingProvider):
    def __init__(self):
        self.api_url = f"https://graph.facebook.com/v17.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    def send_message(self, recipient_id: str, message: str, **kwargs):
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message},
        }
        response = requests.post(self.api_url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def handle_webhook(self, data: dict):
        # Implementation for Phase 4
        pass
