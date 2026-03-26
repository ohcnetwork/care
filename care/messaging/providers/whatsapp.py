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

    def send_message(self, recipient_id: str, message: str, **kwargs) -> None:
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
            print(f"(WhatsApp Dev Mode) To {recipient_id}: {message}")
            return

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message},
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()

    def handle_webhook(self, data: dict) -> None:
        pass
