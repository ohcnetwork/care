#!/usr/bin/env python3
"""
Test script to check WhatsApp registration functionality
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ashu/care')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DJANGO_READ_DOT_ENV_FILE', 'True')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')

# Setup Django
django.setup()

from care_whatsapp_bot.im_wrapper.whatsapp import WhatsAppProvider
from care_whatsapp_bot.message_router import MessageRouter
from care_whatsapp_bot.im_wrapper.base import IMMessage, MessageType

def test_registration():
    """Test the registration flow"""
    print("🧪 Testing WhatsApp Registration Flow...")
    
    # Create a test message
    test_message = IMMessage(
        sender_id="919876543210",  # New phone number not in database
        message_type=MessageType.TEXT,
        content="register",
        platform="whatsapp",
        timestamp="1642678900",
        metadata={}
    )
    
    print(f"📱 Test message: {test_message.content} from {test_message.sender_id}")
    
    # Initialize message router
    try:
        router = MessageRouter()
        print("✅ Message router initialized successfully")
        
        # Route the message
        responses = router.route_message(test_message)
        print(f"📤 Generated {len(responses)} responses")
        
        for i, response in enumerate(responses):
            print(f"Response {i+1}: {response.content[:100]}...")
            
    except Exception as e:
        print(f"❌ Error during registration test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registration()