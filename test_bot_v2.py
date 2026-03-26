import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from care.messaging.dispatcher import IntentDispatcher
from care.users.models import User
from care.messaging.models import WhatsAppProfile
from care.facility.models.patient import PatientMobileOTP
from django.conf import settings

def test():
    wa_id = "test_bot_1"
    WhatsAppProfile.objects.filter(whatsapp_id=wa_id).delete()
    
    # Force a user for testing
    user = User.objects.first()
    if not user:
        user = User.objects.create(username="bot_test", phone_number="+919000000001")
    elif not user.phone_number or not user.phone_number.startswith("+"):
        user.phone_number = "+91" + "".join([str(i) for i in range(10)])
        user.save()
    
    # 1. Start
    d = IntentDispatcher(wa_id, "/start")
    r = d.dispatch()
    assert "Welcome to CARE!" in r
    print("[PASS] /start")

    # 2. Login - Initiate
    d = IntentDispatcher(wa_id, "/login")
    r = d.dispatch()
    assert "enter your registered phone number" in r.lower()
    print("[PASS] /login prompt")

    # 3. Phone input
    d = IntentDispatcher(wa_id, user.phone_number)
    r = d.dispatch()
    assert "OTP" in r
    print("[PASS] Phone input (OTP triggered)")

    # 4. OTP verification
    # Need to get the latest OTP for this phone
    otp_obj = PatientMobileOTP.objects.filter(phone_number=user.phone_number).latest('created_date')
    d = IntentDispatcher(wa_id, otp_obj.otp)
    r = d.dispatch()
    assert "Success" in r or "linked to" in r.lower()
    print("[PASS] OTP verification")

    # 5. Auth'd command - /meds
    d = IntentDispatcher(wa_id, "/meds")
    r = d.dispatch()
    assert "Medications" in r
    print("[PASS] Authenticated command /meds")

    # 6. Logout
    d = IntentDispatcher(wa_id, "/logout")
    r = d.dispatch()
    assert "Logged out" in r.lower()
    assert not WhatsAppProfile.objects.filter(whatsapp_id=wa_id).exists()
    print("[PASS] /logout")

if __name__ == "__main__":
    try:
        test()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
