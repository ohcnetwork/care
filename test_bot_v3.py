import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from care.messaging.dispatcher import IntentDispatcher
from care.users.models import User
from care.messaging.models import WhatsAppProfile
from care.facility.models.patient import PatientMobileOTP
from care.emr.models.patient import Patient, PatientUser
from care.security.models import RoleModel
from django.conf import settings

def test():
    wa_id = "test_bot_1"
    WhatsAppProfile.objects.filter(whatsapp_id=wa_id).delete()
    
    # 1. Setup User and Patient link
    user = User.objects.first()
    if not user:
        user = User.objects.create(username="bot_test", phone_number="+919000000001")
    elif not user.phone_number or not user.phone_number.startswith("+"):
        user.phone_number = "+91" + "".join([str(i) for i in range(10)])
        user.save()
    
    # Ensure patient link exists for meds/records test
    patient = Patient.objects.all().first()
    if not patient:
        patient = Patient.objects.create(name="Bot Test Patient", phone_number=user.phone_number)
    
    role = RoleModel.objects.all().first()
    if not role:
        role = RoleModel.objects.create(name="Patient", role_type="patient")
        
    PatientUser.objects.get_or_create(user=user, patient=patient, defaults={"role": role})

    # Start Test
    print("--- Start Test ---")
    
    # 1. Start
    r = IntentDispatcher(wa_id, "/start").dispatch()
    assert "Welcome to CARE!" in r
    print("[PASS] /start")

    # 2. Login flow
    IntentDispatcher(wa_id, "/login").dispatch()
    IntentDispatcher(wa_id, user.phone_number).dispatch()
    otp = PatientMobileOTP.objects.filter(phone_number=user.phone_number).latest('created_date').otp
    r = IntentDispatcher(wa_id, otp).dispatch()
    assert "Success" in r or "linked to" in r.lower()
    print("[PASS] Login & Linking")

    # 3. Meds
    r = IntentDispatcher(wa_id, "/meds").dispatch()
    assert "Medications" in r
    print("[PASS] /meds")

    # 4. Records
    r = IntentDispatcher(wa_id, "/records").dispatch()
    assert "Encounters" in r or "records found" in r.lower()
    print("[PASS] /records")

    # 5. Logout
    r = IntentDispatcher(wa_id, "/logout").dispatch()
    assert "Logged out" in r.lower()
    print("[PASS] /logout")

if __name__ == "__main__":
    try:
        test()
        print("\n🎉 BOT INTERACTION VERIFIED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
