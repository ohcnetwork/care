from django.conf import settings

from care.utils.lock import Lock, MultipleItemsLock


class AccountLock(Lock):
    def __init__(self, account, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:account:{account.id}"
        self.timeout = timeout


class InvoiceLock(Lock):
    def __init__(self, invoice, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:invoice:{invoice.id}"
        self.timeout = timeout


class InvoiceCreateLock(Lock):
    def __init__(self, timeout=settings.LOCK_TIMEOUT):
        self.key = "lock:create_invoice"
        self.timeout = timeout


class PatientCreateLock(Lock):
    def __init__(self, timeout=settings.LOCK_TIMEOUT):
        self.key = "lock:create_patient"
        self.timeout = timeout


class ChargeItemLock(Lock):
    def __init__(self, charge_item, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:charge_item:{charge_item.id}"
        self.timeout = timeout


class ChargeItemsLock(MultipleItemsLock):
    def get_key(self, key):
        return f"lock:charge_item:{key}"


class InventoryItemLock(Lock):
    def __init__(self, inventory_item, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:inventory_item:{inventory_item.id}"
        self.timeout = timeout
