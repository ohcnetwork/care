import logging
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django.conf import settings
from care.messaging.providers.whatsapp import WhatsAppProvider
from care.messaging.dispatcher import IntentDispatcher

logger = logging.getLogger(__name__)

class WhatsAppWebhookViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    
    def list(self, request):
        verify_token = request.query_params.get("hub.verify_token")
        mode = request.query_params.get("hub.mode")
        challenge = request.query_params.get("hub.challenge")
        
        if mode == "subscribe" and verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            return Response(int(challenge), status=status.HTTP_200_OK)
        return Response("Invalid token", status=status.HTTP_403_FORBIDDEN)

    def create(self, request):
        data = request.data
        if "object" in data and data["object"] == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        from_id = message.get("from")
                        text_body = message.get("text", {}).get("body")
                        
                        if not from_id or not text_body:
                            continue
                            
                        # Dispatch the intent
                        dispatcher = IntentDispatcher(from_id, text_body)
                        response_text = dispatcher.dispatch()
                        
                        # Send the response back
                        provider = WhatsAppProvider()
                        provider.send_message(from_id, response_text)
                        
            return Response(status=status.HTTP_200_OK)
            
        return Response(status=status.HTTP_400_BAD_REQUEST)
