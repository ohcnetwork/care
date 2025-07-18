import json
import logging
from typing import Dict, Any

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings

from .im_wrapper.whatsapp import WhatsAppProvider
from .message_router import MessageRouter
from .utils.data_formatter import DataFormatter

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """Handle WhatsApp webhook requests"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.whatsapp_provider = WhatsAppProvider({})
        self.message_router = MessageRouter()
        self.formatter = DataFormatter()
    
    def get(self, request):
        """Handle webhook verification"""
        try:
            mode = request.GET.get('hub.mode')
            token = request.GET.get('hub.verify_token')
            challenge = request.GET.get('hub.challenge')
            
            logger.info(f"Webhook verification request: mode={mode}, token={token}")
            
            response_challenge = self.whatsapp_provider.verify_webhook(mode, token, challenge)
            
            if response_challenge:
                logger.info("Webhook verification successful")
                return HttpResponse(response_challenge, content_type='text/plain')
            else:
                logger.warning("Webhook verification failed")
                return HttpResponseForbidden("Verification failed")
        
        except Exception as e:
            logger.error(f"Error in webhook verification: {e}")
            return HttpResponseBadRequest("Verification error")
    
    def post(self, request):
        """Handle incoming WhatsApp messages"""
        try:
            body = request.body.decode('utf-8')
            signature = request.headers.get('X-Hub-Signature-256', '')
            if not self.whatsapp_provider.validate_webhook_signature(body, signature):
                logger.warning("Invalid webhook signature")
                return HttpResponseForbidden("Invalid signature")
            
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON payload: {e}")
                return HttpResponseBadRequest("Invalid JSON")
            self._process_webhook(payload)
            
            return HttpResponse("OK", content_type='text/plain')
        
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return HttpResponse("OK", content_type='text/plain')  # Always return OK to WhatsApp
    
    def _process_webhook(self, payload: Dict[str, Any]) -> None:
        """Process incoming webhook payload"""
        try:
            incoming_message = self.whatsapp_provider.parse_incoming_message(payload)
            
            if not incoming_message:
                logger.info("No message to process in webhook payload")
                return
            
            logger.info(f"Processing message from {incoming_message.sender_id}: {incoming_message.content[:100]}")
            
            responses = self.message_router.route_message(incoming_message)
            for response in responses:
                try:
                    success = self.whatsapp_provider.send_message(response)
                    if success:
                        logger.info(f"Response sent to {response.recipient_id}")
                    else:
                        logger.error(f"Failed to send response to {response.recipient_id}")
                except Exception as e:
                    logger.error(f"Error sending response: {e}")
        
        except Exception as e:
            logger.error(f"Error processing webhook payload: {e}")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """Function-based view for WhatsApp webhook (alternative to class-based view)"""
    view = WhatsAppWebhookView()
    return view.dispatch(request)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for the WhatsApp bot"""
    try:
        health_status = {
            'status': 'healthy',
            'service': 'CARE WhatsApp Bot',
            'version': '1.0.0'
        }
        whatsapp_provider = WhatsAppProvider({})
        if not whatsapp_provider.access_token:
            health_status['warnings'] = ['WhatsApp access token not configured']
        
        return HttpResponse(
            json.dumps(health_status),
            content_type='application/json'
        )
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HttpResponse(
            json.dumps({
                'status': 'unhealthy',
                'error': str(e)
            }),
            content_type='application/json',
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def send_test_message(request):
    """Test endpoint to send a message (for development/testing)"""
    try:
        if not settings.DEBUG:
            return HttpResponseForbidden("Not available in production")
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        
        phone_number = data.get('phone_number')
        message = data.get('message')
        
        if not phone_number or not message:
            return HttpResponseBadRequest("phone_number and message are required")
        from .im_wrapper.base import IMResponse, MessageType
        
        whatsapp_provider = WhatsAppProvider({})
        response = IMResponse(
            recipient_id=phone_number,
            message_type=MessageType.TEXT,
            content=message
        )
        
        success = whatsapp_provider.send_message(response)
        
        return HttpResponse(
            json.dumps({
                'success': success,
                'message': 'Test sent' if success else 'Test failed'
            }),
            content_type='application/json'
        )
    
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }),
            content_type='application/json',
            status=500
        )