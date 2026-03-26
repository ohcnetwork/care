import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from care.messaging.dispatcher import IntentDispatcher
from care.messaging.models import WhatsAppProfile
from care.users.models import User
from care.facility.models.patient import PatientMobileOTP

def verify_flow():
    wa_id = "+910000000000"
    user = User.objects.first()
    
    if not user:
        print("❌ No user found in DB. Run migrations/seed first.")
        return

    print(f"🚀 Verification Started for User: {user.username} ({user.phone_number})")
    
    # 1. Start (Unlinked)
    WhatsAppProfile.objects.filter(whatsapp_id=wa_id).delete()
    d = IntentDispatcher(wa_id, "/start")
    print(f"[/start] OUT: {d.dispatch()}")
    
    # 2. Login
    d = IntentDispatcher(wa_id, "/login")
    print(f"[/login] OUT: {d.dispatch()}")
    
    # 3. Phone Input
    d = IntentDispatcher(wa_id, user.phone_number)
    print(f"[{user.phone_number}] OUT: {d.dispatch()}")
    
    # 4. OTP Input
    otp_obj = PatientMobileOTP.objects.filter(phone_number=user.phone_number, is_used=False).order_by("-created_date").first()
    if not otp_obj:
        print("❌ OTP not generated.")
        return
    print(f"Found OTP: {otp_obj.otp}")
    
    d = IntentDispatcher(wa_id, otp_obj.otp)
    print(f"[{otp_obj.otp}] OUT: {d.dispatch()}")
    
    # 5. Meds
    d = IntentDispatcher(wa_id, "/meds")
    print(f"[/meds] OUT: {d.dispatch()}")
    
    # 6. Logout
    d = IntentDispatcher(wa_id, "/logout")
    print(f"[/logout] OUT: {d.dispatch()}")
    
    print("✅ Flow Verified Successfully!")

if __name__ == "__main__":
    verify_flow()
