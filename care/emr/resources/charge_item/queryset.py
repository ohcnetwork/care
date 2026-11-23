from django.db.models import Prefetch

from care.emr.models.invoice import Invoice


def charge_items_for_serialization(queryset):
    # Prefetch the owning invoice once. Joining it repeats its growing charge
    # item snapshot for every item, even though the nested read spec omits it.
    return queryset.select_related("charge_item_definition").prefetch_related(
        # Share category instances so expired parent caches refresh only once.
        "charge_item_definition__category",
        Prefetch(
            "paid_invoice",
            queryset=Invoice.objects.select_related("account").defer(
                "charge_items",
                "charge_items_copy",
                "total_price_components",
                "lock_history",
                "history",
            ),
        ),
    )
