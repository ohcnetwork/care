import random
import string
import logging
from django.core.cache import cache
from django.conf import settings
from care.messaging.models import WhatsAppProfile
from care.messaging.providers.whatsapp import WhatsAppProvider
from care.emr.models.medication_request import MedicationRequest
from care.emr.models.encounter import Encounter
from care.emr.models.device import Device
from care.emr.models.patient import Patient
from care.emr.resources.medication.request.spec import MedicationRequestReadSpec
from care.emr.resources.encounter.spec import EncounterListSpec
from care.facility.models.patient import PatientMobileOTP
from care.users.models import User
from care.utils import sms

logger = logging.getLogger(__name__)

STATE_IDLE = "IDLE"
STATE_AWAITING_PHONE = "AWAITING_PHONE"
STATE_AWAITING_OTP = "AWAITING_OTP"

class IntentDispatcher:
    def __init__(self, whatsapp_id, message_body):
        self.whatsapp_id = whatsapp_id
        self.message = message_body.strip()
        self.cache_key = f"wa_bot_state:{self.whatsapp_id}"
        self.state = cache.get(self.cache_key, {"state": STATE_IDLE})
        self.user = self._get_user()

    def _get_user(self):
        profile = WhatsAppProfile.objects.filter(whatsapp_id=self.whatsapp_id).first()
        return profile.user if profile else None

    def dispatch(self) -> str:
        current_state = self.state.get("state")

        if current_state == STATE_AWAITING_PHONE:
            return self.handle_phone_input()
        
        if current_state == STATE_AWAITING_OTP:
            return self.handle_otp_input()

        # Handle Commands
        cmd = self.message.lower().split()[0] if self.message else ""
        if cmd in ["/start", "/hi", "hi", "hello"]:
            return self.handle_start()
        elif cmd == "/login":
            return self.prompt_phone()
        elif cmd == "/logout":
            return self.handle_logout()
        elif cmd == "/help":
            return self.handle_help()
        elif cmd == "/meds":
            return self.handle_meds()
        elif cmd == "/records":
            return self.handle_records()
        elif cmd == "/assets":
            return self.handle_assets()
        
        return "I'm sorry, I don't understand that command. Type /help to see what I can do."

    def set_state(self, state_name, **kwargs):
        new_state = {"state": state_name, **kwargs}
        cache.set(self.cache_key, new_state, timeout=600)

    def clear_state(self):
        cache.delete(self.cache_key)

    def handle_start(self):
        if self.user:
            return f"Welcome back, *{self.user.username}*! 👋\nHow can I help you today? Type /help for options."
        return "Welcome to CARE! 👋\nI am your digital health assistant. To access your records or facility data, please link your account by typing /login."

    def handle_logout(self):
        if not self.user:
            return "You are not currently logged in / linked."
        
        WhatsAppProfile.objects.filter(whatsapp_id=self.whatsapp_id).delete()
        self.clear_state()
        return "✅ Logged out successfully. Your WhatsApp ID is now unlinked from the CARE system."

    def handle_help(self):
        help_text = "🛠️ *Available Commands:*\n\n"
        if not self.user:
            help_text += "• /login - Link your WhatsApp ID\n"
        else:
            help_text += "• /hi - Greeting\n"
            help_text += "• /meds - View your active medications\n"
            help_text += "• /records - View your patient records\n"
            
            if self.user.is_superuser or self.user.user_type != "Patient": 
                help_text += "• /assets - View device inventory at your facility\n"
            
            help_text += "• /logout - Unlink this WhatsApp ID\n"
        
        return help_text

    def prompt_phone(self):
        self.set_state(STATE_AWAITING_PHONE)
        return "Please enter your registered phone number (e.g., +919000000000):"

    def handle_phone_input(self):
        phone_number = self.message
        if not phone_number.startswith("+") or len(phone_number) < 10:
            return "Invalid format. Please enter a full phone number starting with +."
        
        user = User.objects.filter(phone_number=phone_number).first()
        if not user:
            return "No user found with this phone number. Please contact your administrator."

        otp = "".join(random.choices(string.digits, k=settings.OTP_LENGTH))
        PatientMobileOTP.objects.create(phone_number=phone_number, otp=otp)
        
        self.set_state(STATE_AWAITING_OTP, phone_number=phone_number)

        if settings.USE_SMS:
            try:
                sms.send_text_message(
                    content=f"Your CARE WhatsApp linking OTP is {otp}",
                    recipients=[phone_number]
                )
                return "An OTP has been sent. Please enter the code here."
            except Exception:
                return "Error sending SMS. Please try again later."
        else:
            logger.info(f"OTP for {phone_number} is {otp} (Console)")
            return f"(Dev Mode) Your OTP is *{otp}*. Please enter it here to verify."

    def handle_otp_input(self):
        otp = self.message
        phone_number = self.state.get("phone_number")
        
        otp_obj = PatientMobileOTP.objects.filter(
            phone_number=phone_number, otp=otp, is_used=False
        ).order_by("-created_date").first()

        if not otp_obj:
            return "❌ Invalid or expired OTP."

        otp_obj.is_used = True
        otp_obj.save()

        user = User.objects.get(phone_number=phone_number)
        WhatsAppProfile.objects.update_or_create(
            whatsapp_id=self.whatsapp_id,
            defaults={"user": user, "is_verified": True, "can_receive_ppi": True}
        )

        self.clear_state()
        return f"✅ Linked to *{user.username}*! Try /meds or /records."

    def handle_meds(self):
        if not self._check_auth(): return self._auth_error()
        
        # Correctly filter Medications for the linked user's patient profiles
        meds = MedicationRequest.objects.filter(patient__patientuser__user=self.user, status="active")
        if not meds.exists():
            return "You have no active Medications."
        
        response = "💊 *Active Medications:*\n"
        for med in meds:
            data = MedicationRequestReadSpec.serialize(med).to_json()
            name = data.get("medication", {}).get("display", "Unnamed")
            response += f"• {name}\n"
        return response

    def handle_records(self):
        if not self._check_auth(): return self._auth_error()
        
        # Correctly filter Encounters for the linked user's patient profiles
        encounters = Encounter.objects.filter(patient__patientuser__user=self.user).order_by("-created_date")[:5]
        if not encounters.exists():
            return "No patient records found."
        
        response = "📊 *Recent Encounters:*\n"
        for enc in encounters:
            data = EncounterListSpec.serialize(enc).to_json()
            date = enc.created_date.strftime("%d %b %Y")
            status = data.get("status", "Unknown")
            response += f"• {date}: {status.capitalize()}\n"
        return response

    def handle_assets(self):
        if not self.user: return self._auth_error()
        if not self.user.home_facility:
            return "You are not associated with any facility."
            
        devices = Device.objects.filter(facility=self.user.home_facility)[:10]
        if not devices.exists():
            return "No devices/assets found in your facility."
            
        response = f"🏢 *Assets at {self.user.home_facility.name}:*\n"
        for dev in devices:
            name = dev.user_friendly_name or dev.registered_name or "Unknown Device"
            response += f"• {name} ({dev.availability_status})\n"
        return response

    def _check_auth(self):
        profile = getattr(self.user, "whatsapp_profile", None) if self.user else None
        return bool(profile and profile.can_receive_ppi)

    def _auth_error(self):
        return "🔒 Please /login to access this information."
