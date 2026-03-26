from django.contrib import admin
from care.messaging.models import WhatsAppProfile


@admin.register(WhatsAppProfile)
class WhatsAppProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "whatsapp_id", "is_verified", "can_receive_ppi")
    search_fields = ("user__username", "whatsapp_id")
