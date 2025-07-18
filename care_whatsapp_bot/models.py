from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from care.emr.models.patient import Patient

User = get_user_model()


class WhatsAppSession(models.Model):
    
    phone_number = models.CharField(max_length=20, db_index=True)
    user_type = models.CharField(
        max_length=20,
        choices=[
            ('patient', 'Patient'),
            ('hospital_staff', 'Hospital Staff'),
            ('unknown', 'Unknown')
        ]
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='whatsapp_sessions'
    )
    staff_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='whatsapp_sessions'
    )
    
    is_authenticated = models.BooleanField(default=False)
    authenticated_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    session_expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'whatsapp_sessions'
        indexes = [
            models.Index(fields=['phone_number', 'is_authenticated']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"WhatsApp Session: {self.phone_number} ({self.user_type})"
    
    def is_session_valid(self):
        if not self.is_authenticated:
            return False
        
        if self.session_expires_at and timezone.now() > self.session_expires_at:
            return False
        
        return True
    
    def extend_session(self, hours=24):
        from datetime import timedelta
        self.session_expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['session_expires_at', 'updated_at'])


class WhatsAppMessage(models.Model):
    
    DIRECTION_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('location', 'Location'),
        ('contact', 'Contact'),
    ]
    
    whatsapp_message_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    session = models.ForeignKey(
        WhatsAppSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages'
    )
    
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'whatsapp_messages'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['phone_number', 'direction']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"WhatsApp Message: {self.phone_number} ({self.direction}) - {self.content[:50]}"
    
    def mark_processed(self, error=None):
        self.processed = True
        self.processed_at = timezone.now()
        if error:
            self.error_message = str(error)
        self.save(update_fields=['processed', 'processed_at', 'error_message'])


class WhatsAppCommand(models.Model):
    
    COMMAND_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('verify_otp', 'Verify OTP'),
        ('get_records', 'Get Records'),
        ('get_medications', 'Get Medications'),
        ('get_appointments', 'Get Appointments'),
        ('get_procedures', 'Get Procedures'),
        ('patient_search', 'Patient Search'),
        ('patient_info', 'Patient Info'),
        ('schedule_appointment', 'Schedule Appointment'),
        ('help', 'Help'),
        ('menu', 'Menu'),
        ('unknown', 'Unknown'),
    ]
    
    phone_number = models.CharField(max_length=20, db_index=True)
    command = models.CharField(max_length=30, choices=COMMAND_CHOICES)
    command_args = models.JSONField(default=dict, blank=True)
    
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    execution_time_ms = models.IntegerField(null=True, blank=True)
    
    session = models.ForeignKey(
        WhatsAppSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commands'
    )
    message = models.ForeignKey(
        WhatsAppMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commands'
    )
    
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'whatsapp_commands'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['phone_number', 'command']),
            models.Index(fields=['executed_at']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"WhatsApp Command: {self.phone_number} - {self.command}"


class WhatsAppNotification(models.Model):
    
    NOTIFICATION_TYPE_CHOICES = [
        ('appointment_reminder', 'Appointment Reminder'),
        ('medication_reminder', 'Medication Reminder'),
        ('test_result', 'Test Result'),
        ('discharge_summary', 'Discharge Summary'),
        ('system_alert', 'System Alert'),
        ('custom', 'Custom'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]
    
    phone_number = models.CharField(max_length=20, db_index=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    whatsapp_message_id = models.CharField(max_length=100, null=True, blank=True)
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='whatsapp_notifications'
    )
    
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'whatsapp_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"WhatsApp Notification: {self.phone_number} - {self.title}"
    
    def mark_sent(self, whatsapp_message_id=None):
        self.status = 'sent'
        self.sent_at = timezone.now()
        if whatsapp_message_id:
            self.whatsapp_message_id = whatsapp_message_id
        self.save(update_fields=['status', 'sent_at', 'whatsapp_message_id'])
    
    def mark_delivered(self):
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_read(self):
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])