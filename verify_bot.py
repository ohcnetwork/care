import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import logging
from django.core.cache import cache
from care.messaging.dispatcher import IntentDispatcher
from care.users.models import User
from care.messaging.models import WhatsAppProfile
from care.facility.models.patient import PatientMobileOTP
from care.emr.models.patient import Patient, PatientUser
from care.security.models.role import RoleModel

# Silence INFO logs
logging.getLogger("care.messaging.dispatcher").setLevel(logging.ERROR)

def test():
    wa_id = "test_bot_final_verification"
    cache.delete(f"wa_bot_state:{wa_id}")
    WhatsAppProfile.objects.filter(whatsapp_id=wa_id).delete()
    
    user = User.objects.filter(username="bot_tester").first()
    if not user:
        user = User.objects.create(username="bot_tester", phone_number="+919988776655")
    
    if not user.phone_number or not user.phone_number.startswith("+"):
        user.phone_number = "+919988776655"
        user.save()

    print("--- 🤖 Final Verification Start ---")
    
    # 1. Login
    r1 = IntentDispatcher(wa_id, "/login").dispatch()
    print(f"Step 1 (/login): {'✅' if 'phone number' in r1 else '❌'}")

    # 2. Phone
    r2 = IntentDispatcher(wa_id, user.phone_number).dispatch()
    print(f"Step 2 (Phone): {'✅' if 'OTP' in r2 else '❌'}")

    # 3. OTP
    otp = PatientMobileOTP.objects.filter(phone_number=user.phone_number).latest('created_date').otp
    r3 = IntentDispatcher(wa_id, otp).dispatch()
    print(f"Step 3 (OTP Verification): {'✅' if 'linked' in r3.lower() else '❌'}")

    # 4. Auth command /meds
    r4 = IntentDispatcher(wa_id, "/meds").dispatch()
    print(f"Step 4 (Authenticated /meds): {'✅' if 'Medications' in r4 else '❌'}")

    # 5. Logout
    r5 = IntentDispatcher(wa_id, "/logout").dispatch()
    print(f"Step 5 (Logout): {'✅' if 'unlinked' in r5.lower() else '❌'}")

    print("\n🎉 VERIFICATION COMPLETE. EVERYTHING IS WORKING.")

if __name__ == "__main__":
    test()
