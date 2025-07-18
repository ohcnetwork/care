from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppCommand,
    WhatsAppNotification
)


@admin.register(WhatsAppSession)
class WhatsAppSessionAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number',
        'user_type',
        'is_authenticated',
        'last_activity',
        'session_status',
        'created_at'
    ]
    list_filter = [
        'user_type',
        'is_authenticated',
        'created_at',
        'last_activity'
    ]
    search_fields = ['phone_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('phone_number', 'user_type')
        }),
        ('User Links', {
            'fields': ('patient', 'staff_user')
        }),
        ('Session Status', {
            'fields': (
                'is_authenticated',
                'authenticated_at',
                'last_activity',
                'session_expires_at'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def session_status(self, obj):
        if obj.is_session_valid():
            return format_html(
                '<span style="color: green;">✓ Valid</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Expired</span>'
            )
    session_status.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient', 'staff_user'
        )


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number',
        'direction',
        'message_type',
        'content_preview',
        'processed',
        'timestamp'
    ]
    list_filter = [
        'direction',
        'message_type',
        'processed',
        'timestamp'
    ]
    search_fields = ['phone_number', 'content']
    readonly_fields = [
        'whatsapp_message_id',
        'timestamp',
        'created_at',
        'processed_at'
    ]
    
    fieldsets = (
        ('Message Information', {
            'fields': (
                'whatsapp_message_id',
                'phone_number',
                'direction',
                'message_type'
            )
        }),
        ('Content', {
            'fields': ('content', 'metadata')
        }),
        ('Processing', {
            'fields': (
                'processed',
                'processed_at',
                'error_message'
            )
        }),
        ('Relationships', {
            'fields': ('session',)
        }),
        ('Timestamps', {
            'fields': ('timestamp', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')


@admin.register(WhatsAppCommand)
class WhatsAppCommandAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number',
        'command',
        'success',
        'execution_time_ms',
        'executed_at'
    ]
    list_filter = [
        'command',
        'success',
        'executed_at'
    ]
    search_fields = ['phone_number']
    readonly_fields = ['executed_at']
    
    fieldsets = (
        ('Command Information', {
            'fields': (
                'phone_number',
                'command',
                'command_args'
            )
        }),
        ('Execution Details', {
            'fields': (
                'success',
                'error_message',
                'execution_time_ms'
            )
        }),
        ('Relationships', {
            'fields': ('session', 'message')
        }),
        ('Timestamps', {
            'fields': ('executed_at',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'session', 'message'
        )


@admin.register(WhatsAppNotification)
class WhatsAppNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number',
        'notification_type',
        'title',
        'status',
        'scheduled_at',
        'sent_at'
    ]
    list_filter = [
        'notification_type',
        'status',
        'scheduled_at',
        'sent_at'
    ]
    search_fields = ['phone_number', 'title', 'message']
    readonly_fields = [
        'whatsapp_message_id',
        'sent_at',
        'delivered_at',
        'read_at',
        'created_at'
    ]
    
    fieldsets = (
        ('Notification Information', {
            'fields': (
                'phone_number',
                'notification_type',
                'title',
                'message'
            )
        }),
        ('Status Tracking', {
            'fields': (
                'status',
                'whatsapp_message_id',
                'scheduled_at',
                'sent_at',
                'delivered_at',
                'read_at'
            )
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Relationships', {
            'fields': ('patient',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_sent', 'mark_as_failed']
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='sent',
            sent_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} notifications marked as sent.'
        )
    mark_as_sent.short_description = 'Mark selected notifications as sent'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'sent']).update(
            status='failed'
        )
        self.message_user(
            request,
            f'{updated} notifications marked as failed.'
        )
    mark_as_failed.short_description = 'Mark selected notifications as failed'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')


admin.site.site_header = 'CARE WhatsApp Bot Administration'
admin.site.site_title = 'CARE WhatsApp Bot Admin'
admin.site.index_title = 'WhatsApp Bot Management'