from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from care_whatsapp_bot.models import WhatsAppNotification
from care.emr.models.patient import Patient
import json


class Command(BaseCommand):
    help = 'Send WhatsApp messages to patients using the existing notification system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Patient phone number (e.g., 918767341918)'
        )
        parser.add_argument(
            '--message',
            type=str,
            required=True,
            help='Message content to send'
        )
        parser.add_argument(
            '--title',
            type=str,
            default='CARE Notification',
            help='Message title (optional)'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='system_alert',
            choices=['system_alert', 'appointment_reminder', 'medication_reminder', 'custom'],
            help='Notification type'
        )
        parser.add_argument(
            '--bulk',
            type=str,
            help='JSON file with bulk messages (format: [{"phone": "123", "message": "text", "title": "title"}])'
        )
        parser.add_argument(
            '--template',
            type=str,
            choices=['welcome', 'appointment_reminder', 'medication_reminder', 'test'],
            help='Use predefined message template'
        )

    def handle(self, *args, **options):
        if options['bulk']:
            self.handle_bulk_messages(options['bulk'])
        elif options['template']:
            self.handle_template_message(options)
        else:
            self.handle_single_message(options)

    def handle_single_message(self, options):
        """Send a single message"""
        phone = options['phone']
        message = options['message']
        title = options['title']
        notification_type = options['type']
        
        try:
            # Try to find the patient
            patient = None
            try:
                patient = Patient.objects.filter(phone_number=phone).first()
                if patient:
                    self.stdout.write(f"📋 Found patient: {patient.name}")
                else:
                    self.stdout.write(f"⚠️  Patient not found for phone {phone}")
            except Exception as e:
                self.stdout.write(f"⚠️  Could not lookup patient: {e}")
            
            # Create notification
            notification = WhatsAppNotification.objects.create(
                phone_number=phone,
                notification_type=notification_type,
                title=title,
                message=message,
                patient=patient,
                scheduled_at=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Message queued successfully!\n"
                    f"📱 Phone: {phone}\n"
                    f"📝 Title: {title}\n"
                    f"💬 Message: {message[:50]}{'...' if len(message) > 50 else ''}\n"
                    f"🆔 Notification ID: {notification.id}"
                )
            )
            
        except Exception as e:
            raise CommandError(f"Failed to send message: {e}")

    def handle_bulk_messages(self, bulk_file):
        """Send multiple messages from JSON file"""
        try:
            with open(bulk_file, 'r') as f:
                messages = json.load(f)
            
            self.stdout.write(f"📦 Processing {len(messages)} bulk messages...")
            
            success_count = 0
            for i, msg_data in enumerate(messages, 1):
                try:
                    phone = msg_data['phone']
                    message = msg_data['message']
                    title = msg_data.get('title', 'CARE Notification')
                    notification_type = msg_data.get('type', 'system_alert')
                    
                    # Find patient
                    patient = None
                    try:
                        patient = Patient.objects.filter(phone_number=phone).first()
                    except:
                        pass
                    
                    # Create notification
                    notification = WhatsAppNotification.objects.create(
                        phone_number=phone,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        patient=patient,
                        scheduled_at=timezone.now()
                    )
                    
                    self.stdout.write(f"  {i}. ✅ {phone} - ID: {notification.id}")
                    success_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  {i}. ❌ {msg_data.get('phone', 'unknown')}: {e}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Bulk send completed: {success_count}/{len(messages)} successful")
            )
            
        except Exception as e:
            raise CommandError(f"Failed to process bulk file: {e}")

    def handle_template_message(self, options):
        """Send a message using predefined templates"""
        phone = options['phone']
        template = options['template']
        
        templates = {
            'welcome': {
                'title': 'Welcome to CARE',
                'message': '''🏥 Welcome to CARE WhatsApp Bot!

We're here to help you with your healthcare needs.

📋 Available commands:
• Type "menu" - See all options
• Type "help" - Get assistance
• Type "appointments" - View your appointments
• Type "records" - Access medical records

How can we assist you today?''',
                'type': 'system_alert'
            },
            'appointment_reminder': {
                'title': 'Appointment Reminder',
                'message': '''🏥 Appointment Reminder

📅 You have an upcoming appointment:
⏰ Tomorrow at 2:00 PM
👨‍⚕️ Dr. Smith
🏥 Main Hospital

Please arrive 15 minutes early.

Reply "reschedule" if you need to change the time.''',
                'type': 'appointment_reminder'
            },
            'medication_reminder': {
                'title': 'Medication Reminder',
                'message': '''💊 Medication Reminder

⏰ Time to take your medication!

📋 Please take:
• Morning dose as prescribed
• With food if required

Stay healthy! 🌟

Reply "taken" to confirm.''',
                'type': 'medication_reminder'
            },
            'test': {
                'title': 'Test Message',
                'message': '''🧪 This is a test message from CARE Bot.

If you receive this, the WhatsApp integration is working correctly!

✅ System Status: Online
📱 Bot Version: 1.0
🕐 Sent at: ''' + timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'system_alert'
            }
        }
        
        if template not in templates:
            raise CommandError(f"Unknown template: {template}")
        
        template_data = templates[template]
        
        # Override with command line options if provided
        if options.get('title') != 'CARE Notification':
            template_data['title'] = options['title']
        if options.get('type') != 'system_alert':
            template_data['type'] = options['type']
        
        # Send the message
        try:
            patient = None
            try:
                patient = Patient.objects.filter(phone_number=phone).first()
            except:
                pass
            
            notification = WhatsAppNotification.objects.create(
                phone_number=phone,
                notification_type=template_data['type'],
                title=template_data['title'],
                message=template_data['message'],
                patient=patient,
                scheduled_at=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Template '{template}' sent successfully!\n"
                    f"📱 Phone: {phone}\n"
                    f"🆔 Notification ID: {notification.id}"
                )
            )
            
        except Exception as e:
            raise CommandError(f"Failed to send template message: {e}")