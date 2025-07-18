import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from care.emr.models.patient import Patient
from care.facility.models import User
from care.utils.sms.send_sms import send_sms
from .im_wrapper.base import UserType

logger = logging.getLogger(__name__)
User = get_user_model()


class WhatsAppAuthenticator:
    """Handle authentication for WhatsApp bot users"""
    
    OTP_EXPIRY_MINUTES = 10
    MAX_OTP_ATTEMPTS = 3
    RATE_LIMIT_MINUTES = 5
    
    def __init__(self):
        self.cache_prefix = "whatsapp_bot"
    
    def _get_cache_key(self, phone_number: str, key_type: str) -> str:
        """Generate cache key for storing temporary data"""
        return f"{self.cache_prefix}:{key_type}:{phone_number}"
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number format"""
        phone = ''.join(filter(str.isdigit, phone_number))
        
        if len(phone) == 10:
            phone = f"91{phone}"
        elif phone.startswith('0'):
            phone = f"91{phone[1:]}"
        
        return phone
    
    def identify_user_type(self, phone_number: str) -> Tuple[UserType, Optional[Any]]:
        """Identify if the phone number belongs to a patient or hospital staff"""
        normalized_phone = self._normalize_phone_number(phone_number)
        
        try:
            patient = Patient.objects.filter(
                phone_number__icontains=normalized_phone[-10:]
            ).first()
            if patient:
                return UserType.PATIENT, patient
        except Exception as e:
            logger.error(f"Error checking patient: {e}")
        try:
            # Use only() to select specific fields and avoid missing column issues
            user = User.objects.only(
                'id', 'username', 'first_name', 'last_name', 'phone_number', 'user_type'
            ).filter(
                phone_number__icontains=normalized_phone[-10:]
            ).first()
            if user:
                return UserType.HOSPITAL_STAFF, user
        except Exception as e:
            logger.error(f"Error checking hospital staff: {e}")
        
        return UserType.UNKNOWN, None
    
    def generate_otp(self, phone_number: str) -> Optional[str]:
        """Generate and send OTP for authentication"""
        normalized_phone = self._normalize_phone_number(phone_number)
        
        rate_limit_key = self._get_cache_key(normalized_phone, "rate_limit")
        if cache.get(rate_limit_key):
            logger.warning(f"Rate limit exceeded for phone: {normalized_phone}")
            return None
        
        import random
        otp = str(random.randint(100000, 999999))
        otp_key = self._get_cache_key(normalized_phone, "otp")
        attempts_key = self._get_cache_key(normalized_phone, "attempts")
        
        cache.set(otp_key, otp, timeout=self.OTP_EXPIRY_MINUTES * 60)
        cache.set(attempts_key, 0, timeout=self.OTP_EXPIRY_MINUTES * 60)
        
        try:
            message = f"Your CARE WhatsApp Bot verification code is: {otp}. Valid for {self.OTP_EXPIRY_MINUTES} minutes."
            send_sms(normalized_phone, message)
            logger.info(f"OTP sent to {normalized_phone}")
            return otp
        except Exception as e:
            logger.error(f"Error sending OTP to {normalized_phone}: {e}")
            return None
    
    def verify_otp(self, phone_number: str, otp: str) -> bool:
        """Verify OTP for authentication"""
        normalized_phone = self._normalize_phone_number(phone_number)
        
        otp_key = self._get_cache_key(normalized_phone, "otp")
        attempts_key = self._get_cache_key(normalized_phone, "attempts")
        rate_limit_key = self._get_cache_key(normalized_phone, "rate_limit")
        
        stored_otp = cache.get(otp_key)
        attempts = cache.get(attempts_key, 0)
        
        if not stored_otp:
            logger.warning(f"No OTP found or expired for phone: {normalized_phone}")
            return False
        
        if attempts >= self.MAX_OTP_ATTEMPTS:
            logger.warning(f"Max OTP attempts exceeded for phone: {normalized_phone}")
            # Set rate limit
            cache.set(rate_limit_key, True, timeout=self.RATE_LIMIT_MINUTES * 60)
            # Clear OTP data
            cache.delete(otp_key)
            cache.delete(attempts_key)
            return False
        
        if stored_otp == otp:
            cache.delete(otp_key)
            cache.delete(attempts_key)
            
            self._create_auth_session(normalized_phone)
            logger.info(f"OTP verified successfully for phone: {normalized_phone}")
            return True
        else:
            cache.set(attempts_key, attempts + 1, timeout=self.OTP_EXPIRY_MINUTES * 60)
            logger.warning(f"Invalid OTP for phone: {normalized_phone}")
            return False
    
    def _create_auth_session(self, phone_number: str) -> None:
        """Create authenticated session for the user"""
        session_key = self._get_cache_key(phone_number, "session")
        session_data = {
            'phone_number': phone_number,
            'authenticated_at': timezone.now().isoformat(),
            'expires_at': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        
        cache.set(session_key, session_data, timeout=24 * 60 * 60)
    
    def is_authenticated(self, phone_number: str) -> bool:
        """Check if user is authenticated"""
        normalized_phone = self._normalize_phone_number(phone_number)
        session_key = self._get_cache_key(normalized_phone, "session")
        
        session_data = cache.get(session_key)
        if not session_data:
            return False
        
        expires_at = datetime.fromisoformat(session_data['expires_at'])
        if timezone.now() > expires_at:
            cache.delete(session_key)
            return False
        
        return True
    
    def logout(self, phone_number: str) -> None:
        """Logout user by clearing session"""
        normalized_phone = self._normalize_phone_number(phone_number)
        session_key = self._get_cache_key(normalized_phone, "session")
        cache.delete(session_key)
        logger.info(f"User logged out: {normalized_phone}")
    
    def get_user_context(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user context for authenticated user"""
        if not self.is_authenticated(phone_number):
            return None
        
        user_type, user_obj = self.identify_user_type(phone_number)
        
        if user_type == UserType.PATIENT and user_obj:
            return {
                'user_type': UserType.PATIENT,
                'patient_id': user_obj.external_id,
                'name': user_obj.name,
                'phone_number': phone_number,
                'organization_id': getattr(user_obj, 'organization_id', None)
            }
        elif user_type == UserType.HOSPITAL_STAFF and user_obj:
            return {
                'user_type': UserType.HOSPITAL_STAFF,
                'user_id': user_obj.id,
                'name': f"{user_obj.first_name} {user_obj.last_name}".strip(),
                'phone_number': phone_number,
                'username': user_obj.username,
                'user_type_detail': getattr(user_obj, 'user_type', 'unknown')
            }
        
        return None