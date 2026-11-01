from contextlib import contextmanager

from django.conf import settings
from django.db import OperationalError, transaction
from rest_framework.exceptions import ValidationError

from care.utils.lock import Lock, MultipleItemsLock, ObjectLocked


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


class FacilityEncounterCreateLock(Lock):
    def __init__(self, facility_id, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:create_facility_encounter:{facility_id}"
        self.timeout = timeout


class ChargeItemLock(Lock):
    def __init__(self, charge_item, timeout=settings.LOCK_TIMEOUT):
        self.key = f"lock:charge_item:{charge_item.id}"
        self.timeout = timeout


class ChargeItemsLock(MultipleItemsLock):
    def get_key(self, key):
        return f"lock:charge_item:{key}"


def _is_lock_unavailable(exc):
    cause = exc.__cause__
    code = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    return code == "55P03"  # PostgreSQL lock_not_available


class DispenseOrderLock:
    """Lock dispense orders before inventory rows or cancellation snapshots."""

    def __init__(self, order_ids):
        self.order_ids = set(order_ids) - {None}
        self.orders = {}
        self._transaction = transaction.atomic()

    def __enter__(self):
        from care.emr.models.medication_dispense import DispenseOrder

        self._transaction.__enter__()
        try:
            orders = {
                order.pk: order
                for order in DispenseOrder.objects.filter(pk__in=self.order_ids)
                .order_by("pk")
                .select_for_update(nowait=True, no_key=True)
            }
            if len(orders) != len(self.order_ids):
                raise ValidationError("Dispense order not found")
            self.orders = orders
        except BaseException as exc:
            self._transaction.__exit__(type(exc), exc, exc.__traceback__)
            if isinstance(exc, OperationalError) and _is_lock_unavailable(exc):
                raise ObjectLocked from exc
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._transaction.__exit__(exc_type, exc_value, traceback)


class DeliveryOrderLock:
    """Lock delivery orders before inventory rows or cancellation snapshots."""

    def __init__(self, order_ids):
        self.order_ids = set(order_ids) - {None}
        self.orders = {}
        self._transaction = transaction.atomic()

    def __enter__(self):
        from care.emr.models.supply_delivery import DeliveryOrder

        self._transaction.__enter__()
        try:
            orders = {
                order.pk: order
                for order in DeliveryOrder.objects.filter(pk__in=self.order_ids)
                .order_by("pk")
                .select_for_update(nowait=True, no_key=True)
            }
            if len(orders) != len(self.order_ids):
                raise ValidationError("Delivery order not found")
            self.orders = orders
        except BaseException as exc:
            self._transaction.__exit__(type(exc), exc, exc.__traceback__)
            if isinstance(exc, OperationalError) and _is_lock_unavailable(exc):
                raise ObjectLocked from exc
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._transaction.__exit__(exc_type, exc_value, traceback)


class InventoryCreationLock:
    """Use an existing product row to serialize creation of its stock rows."""

    def __init__(self, product):
        self.product = product
        self._transaction = transaction.atomic(using=product._state.db)  # noqa: SLF001

    def __enter__(self):
        self._transaction.__enter__()
        try:
            # NO KEY UPDATE permits foreign-key references to this product while
            # keeping other stock creators out until the outer transaction ends.
            type(self.product).objects.using(
                self.product._state.db  # noqa: SLF001
            ).select_for_update(nowait=True, no_key=True).only("pk").get(
                pk=self.product.pk
            )
        except BaseException as exc:
            self._transaction.__exit__(type(exc), exc, exc.__traceback__)
            if isinstance(exc, OperationalError) and _is_lock_unavailable(exc):
                raise ObjectLocked from exc
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._transaction.__exit__(exc_type, exc_value, traceback)


class InventoryItemLock:
    """Lock stock until the outer transaction commits or rolls back."""

    def __init__(self, inventory_item):
        self.inventory_item = inventory_item
        self._transaction = transaction.atomic(using=inventory_item._state.db)  # noqa: SLF001

    def __enter__(self):
        self._transaction.__enter__()
        try:
            type(self.inventory_item).objects.using(
                self.inventory_item._state.db  # noqa: SLF001
            ).select_for_update(nowait=True).get(pk=self.inventory_item.pk)
            self.inventory_item.refresh_from_db()
        except BaseException as exc:
            self._transaction.__exit__(type(exc), exc, exc.__traceback__)
            if isinstance(exc, OperationalError) and _is_lock_unavailable(exc):
                raise ObjectLocked from exc
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._transaction.__exit__(exc_type, exc_value, traceback)


@contextmanager
def lock_inventory_items(inventory_items):
    """Acquire every affected stock row before any writes, in primary-key order."""
    items = {}
    for item in inventory_items:
        items.setdefault(item.pk, item)
    first_item = next(iter(items.values()), None)
    database = first_item._state.db if first_item else None  # noqa: SLF001
    with transaction.atomic(using=database):
        if items:
            try:
                # Querysets are lazy; evaluate before refreshing stock or writing.
                list(
                    type(first_item)
                    .objects.using(database)
                    .filter(pk__in=items)
                    .order_by("pk")
                    .select_for_update(nowait=True)
                    .values_list("pk", flat=True)
                )
            except OperationalError as exc:
                if _is_lock_unavailable(exc):
                    raise ObjectLocked from exc
                raise
            for item in items.values():
                item.refresh_from_db()
        yield
