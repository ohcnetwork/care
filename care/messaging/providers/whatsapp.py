import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from care.messaging.providers.base import BaseMessagingProvider


class WhatsAppProvider(BaseMessagingProvider):
    def __init__(self):
        # Fetching settings with safety checks
        self.phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        self.access_token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        self.api_version = getattr(settings, "WHATSAPP_API_VERSION", "v17.0")

        # Raise error if not configured in production
        if not self.phone_number_id or not self.access_token:
            if not settings.DEBUG:
                raise ImproperlyConfigured(
                    "WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN must be set for WhatsApp messaging."
                )

        self.api_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def send_message(self, recipient_id: str, message: str, **kwargs) -> None:
        # Dry-run if credentials are missing in DEBUG mode
        if not self.access_token or not self.phone_number_id:
            print(f"(WhatsApp Dev Mode) Sending to {recipient_id}: {message}")
            return

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message},
        }

        # Added 10s timeout to prevent thread blocking
        response = requests.post(
            self.api_url, headers=self.headers, json=payload, timeout=10
        )
        response.raise_for_status()

    def handle_webhook(self, data: dict) -> None:
        pass
