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


class ChargeItemLock(Lock):
    def __init__(self, charge_item, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:charge_item:{charge_item.id}"
        self.timeout = timeout
