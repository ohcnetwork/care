from django.conf import settings

from care.utils.lock import Lock


class AccountLock(Lock):
    def __init__(self, account, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:account:{account.id}"
        self.timeout = timeout


class InvoiceLock(Lock):
    def __init__(self, invoice, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:invoice:{invoice.id}"
        self.timeout = timeout
