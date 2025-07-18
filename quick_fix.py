#!/usr/bin/env python3
"""
Quick diagnostic and fix script for WhatsApp bot configuration issues.
Run this script to identify and fix common problems.
"""

import os
import sys
import requests
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    required_vars = [
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID',
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN'
    ]
    
    missing_vars = []
    with open(env_path) as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=" in content and content.split(f"{var}=")[1].split('\n')[0].strip() == '':
                missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or empty environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ .env file looks good!")
    return True

def test_whatsapp_api():
    """Test WhatsApp API connectivity."""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        print("❌ Missing access token or phone number ID")
        return False
    
    # Test API connectivity
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ WhatsApp API is accessible!")
            return True
        else:
            print(f"❌ WhatsApp API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to WhatsApp API: {e}")
        return False

def print_fix_instructions():
    """Print instructions to fix common issues."""
    print("\n🔧 How to fix the issues:")
    print("\n1. **Get a new access token:**")
    print("   - Go to https://developers.facebook.com/")
    print("   - Select your WhatsApp Business app")
    print("   - Navigate to WhatsApp > API Setup")
    print("   - Generate a new temporary token")
    print("   - Copy the token")
    
    print("\n2. **Update your .env file:**")
    print("   - Open .env file in your editor")
    print("   - Update WHATSAPP_ACCESS_TOKEN=your_new_token")
    print("   - Update WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id")
    
    print("\n3. **Restart your Django server:**")
    print("   - Stop the current server (Ctrl+C)")
    print("   - Run: python manage.py runserver 0.0.0.0:8000")
    
    print("\n4. **Test the fix:**")
    print("   - Run: python manage.py whatsapp_health_check")
    print("   - Or run this script again: python quick_fix.py")

def main():
    print("🏥 CARE WhatsApp Bot - Quick Diagnostic Tool")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('manage.py').exists():
        print("❌ Please run this script from the Django project root directory")
        sys.exit(1)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, trying to load .env manually")
        env_path = Path('.env')
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    
    print("\n🔍 Running diagnostics...")
    
    # Run checks
    env_ok = check_env_file()
    api_ok = test_whatsapp_api() if env_ok else False
    
    print("\n📊 Results:")
    print(f"Environment file: {'✅' if env_ok else '❌'}")
    print(f"WhatsApp API: {'✅' if api_ok else '❌'}")
    
    if not env_ok or not api_ok:
        print_fix_instructions()
    else:
        print("\n🎉 Everything looks good! Your WhatsApp bot should be working.")
        print("\n💡 If you're still having issues, try:")
        print("   - python manage.py whatsapp_health_check --detailed")
        print("   - Check the Django server logs")

if __name__ == "__main__":
    main()