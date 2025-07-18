from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    
    path('webhook/function/', views.whatsapp_webhook, name='whatsapp_webhook_function'),
    
    path('health/', views.health_check, name='health_check'),
    
    path('test/send/', views.send_test_message, name='send_test_message'),
]