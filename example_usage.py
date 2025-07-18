#!/usr/bin/env python
"""
Example usage of CARE WhatsApp automated messaging system.

This demonstrates how to send messages to patients without manually typing them.
"""

import subprocess
import json
import os

def send_via_management_command():
    """
    Example: Using Django management command to send messages
    """
    print("📱 Method 1: Using Django Management Command")
    print("=" * 50)
    
    # Single message
    cmd = [
        'python', 'manage.py', 'send_whatsapp',
        '--phone', '918767341918',
        '--message', 'Hello! This is an automated message from CARE Bot. Your appointment is confirmed for tomorrow at 2 PM.',
        '--title', 'Appointment Confirmation',
        '--type', 'appointment_reminder'
    ]
    
    print("Command to run:")
    print(' '.join(cmd))
    print("\nThis will send the message automatically without manual typing.\n")
    
    # Template message
    template_cmd = [
        'python', 'manage.py', 'send_whatsapp',
        '--phone', '918767341918',
        '--template', 'welcome'
    ]
    
    print("Template message command:")
    print(' '.join(template_cmd))
    print("\nThis sends a predefined welcome message.\n")

def create_bulk_message_file():
    """
    Example: Creating a bulk message file for multiple patients
    """
    print("📦 Method 2: Bulk Messages via JSON File")
    print("=" * 50)
    
    bulk_messages = [
        {
            "phone": "918767341918",
            "title": "Appointment Reminder",
            "message": "🏥 Reminder: You have an appointment tomorrow at 10 AM with Dr. Smith. Please arrive 15 minutes early.",
            "type": "appointment_reminder"
        },
        {
            "phone": "9876543210",
            "title": "Medication Reminder",
            "message": "💊 Don't forget to take your evening medication. Stay healthy!",
            "type": "medication_reminder"
        },
        {
            "phone": "1234567890",
            "title": "Health Tip",
            "message": "🌟 Health Tip: Drink at least 8 glasses of water daily to stay hydrated!",
            "type": "system_alert"
        }
    ]
    
    # Save to file
    with open('bulk_messages.json', 'w') as f:
        json.dump(bulk_messages, f, indent=2)
    
    print("Created bulk_messages.json with sample messages.")
    print("\nTo send these messages, run:")
    print("python manage.py send_whatsapp --bulk bulk_messages.json")
    print("\nThis will send all messages automatically.\n")

def show_python_script_usage():
    """
    Example: Using Python scripts directly
    """
    print("🐍 Method 3: Direct Python Scripts")
    print("=" * 50)
    
    print("1. Simple message script:")
    print("   python send_simple_message.py")
    print("   (Edit the script to change phone number and message)")
    print()
    
    print("2. Advanced messaging script:")
    print("   python send_whatsapp_messages.py")
    print("   (Includes scheduling, bulk sending, and appointment reminders)")
    print()
    
    print("3. From Django shell:")
    print("   python manage.py shell")
    print("   >>> from care_whatsapp_bot.models import WhatsAppNotification")
    print("   >>> from django.utils import timezone")
    print("   >>> WhatsAppNotification.objects.create(")
    print("   ...     phone_number='918767341918',")
    print("   ...     title='Test Message',")
    print("   ...     message='Hello from CARE!',")
    print("   ...     notification_type='system_alert',")
    print("   ...     scheduled_at=timezone.now()")
    print("   ... )")
    print()

def show_automation_examples():
    """
    Examples of how to automate messaging
    """
    print("🤖 Method 4: Automation Examples")
    print("=" * 50)
    
    print("1. Cron job for daily medication reminders:")
    print("   # Add to crontab (crontab -e)")
    print("   0 9 * * * cd /path/to/care && python manage.py send_whatsapp --template medication_reminder --phone 918767341918")
    print()
    
    print("2. Appointment reminders (day before):")
    print("   # Script that queries database for tomorrow's appointments")
    print("   # and sends reminders automatically")
    print()
    
    print("3. Welcome messages for new patients:")
    print("   # Django signal that triggers when new patient is created")
    print("   # (already exists in signals.py)")
    print()
    
    print("4. Bulk health tips:")
    print("   # Weekly script that sends health tips to all patients")
    print("   python manage.py send_whatsapp --bulk weekly_health_tips.json")
    print()

def main():
    print("🏥 CARE WhatsApp Automated Messaging Examples")
    print("=" * 60)
    print()
    print("Instead of manually typing messages, you can use these automated methods:")
    print()
    
    send_via_management_command()
    create_bulk_message_file()
    show_python_script_usage()
    show_automation_examples()
    
    print("✅ Key Benefits:")
    print("   • No manual typing required")
    print("   • Can send to multiple patients at once")
    print("   • Can schedule messages for later")
    print("   • Can use predefined templates")
    print("   • Can automate with cron jobs")
    print("   • All messages go through existing CARE infrastructure")
    print()
    print("📝 Note: All these methods use the existing WhatsAppNotification")
    print("   model and Celery tasks, so messages are sent automatically")
    print("   by the background workers.")

if __name__ == '__main__':
    main()