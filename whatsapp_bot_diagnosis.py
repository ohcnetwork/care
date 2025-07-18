import os
import sys
from urllib.parse import urlencode

import requests


def check_python_version():
    print("=== Python Version Check ===")
    print(f"Current Python version: {sys.version}")

    if sys.version_info < (3, 12):
        print("❌ Python version too old")
        print(
            f"   Current: {sys.version_info.major}.{sys.version_info.minor}, Required: 3.12+"
        )
        return False
    print("✅ Python version is compatible")
    return True


def check_webhook_configuration():
    print("\n=== WhatsApp Webhook Configuration ===")

    # Read environment configuration
    env_file = "/Users/ashu/care/docker/.local.env"
    config = {}

    try:
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    config[key] = value
    except FileNotFoundError:
        print(f"❌ Environment file not found: {env_file}")
        return False

    webhook_url = config.get("WHATSAPP_WEBHOOK_URL", "")
    verify_token = config.get("WHATSAPP_VERIFY_TOKEN", "")
    access_token = config.get("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = config.get("WHATSAPP_PHONE_NUMBER_ID", "")

    print(f"Webhook URL: {webhook_url}")
    print(
        f"Verify Token: {verify_token[:10]}..."
        if verify_token
        else "Verify Token: Not set"
    )
    print(
        f"Access Token: {access_token[:20]}..."
        if access_token
        else "Access Token: Not set"
    )
    print(f"Phone Number ID: {phone_number_id}")

    if not all([webhook_url, verify_token, access_token, phone_number_id]):
        print("❌ Missing WhatsApp configuration")
        return False

    return webhook_url, verify_token, access_token, phone_number_id


def test_webhook_endpoint(webhook_url, verify_token):
    print("\n=== Webhook Endpoint Test ===")

    # Test webhook verification
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "test123",
        "hub.verify_token": verify_token,
    }

    test_url = f"{webhook_url}?{urlencode(params)}"
    print(f"Testing: {test_url}")

    try:
        response = requests.get(test_url, timeout=10)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text[:100]}")

        if response.status_code == 200 and response.text == "test123":
            print("✅ Webhook endpoint working")
            return True
        if response.status_code == 530:
            print("❌ Server is down (Error 530)")
            return False
        print(f"❌ Unexpected response (Status: {response.status_code})")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to webhook endpoint: {e}")
        return False


def check_local_server():
    print("\n=== Local Server Test ===")

    # Try to import Django settings
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
        import django

        django.setup()
        print("✅ Django settings loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Cannot load Django settings: {e}")
        return False


def main():
    print("WhatsApp Bot Diagnosis Report")
    print("=" * 50)

    issues_found = []

    # Check Python version
    if not check_python_version():
        issues_found.append("Python version compatibility")

    # Check webhook configuration
    webhook_config = check_webhook_configuration()
    if not webhook_config:
        issues_found.append("WhatsApp configuration")
    else:
        webhook_url, verify_token, access_token, phone_number_id = webhook_config

        # Test webhook endpoint
        if not test_webhook_endpoint(webhook_url, verify_token):
            issues_found.append("Webhook endpoint accessibility")

    # Check local server
    if not check_local_server():
        issues_found.append("Local Django server")

    # Summary
    print("\n" + "=" * 50)
    print("DIAGNOSIS SUMMARY")
    print("=" * 50)

    if issues_found:
        print("❌ ISSUES FOUND:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")

    else:
        print("✅ No issues found")
        print("   Check WhatsApp Business API logs for details")


if __name__ == "__main__":
    main()
