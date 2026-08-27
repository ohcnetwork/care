from django.conf import settings

from care.utils.lock import Lock


class OTPSendLock(Lock):
    def __init__(self, phone_number, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:otp_send:{phone_number}"
        self.timeout = timeout


class OTPVerifyLock(Lock):
    def __init__(self, phone_number, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:otp_verify:{phone_number}"
        self.timeout = timeout
