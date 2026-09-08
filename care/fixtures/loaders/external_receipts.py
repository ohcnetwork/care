from datetime import timedelta

from django.utils import timezone

from care.fixtures.loaders.facility import get_or_create_organization
from care.fixtures.loaders.inventory_helpers import (
    finalize_order_headers,
    index_rows_by_ref,
    load_delivery_orders,
    load_request_orders,
    load_supply_deliveries,
    load_supply_requests,
)
from care.fixtures.loaders.load import load_json

_COLLECTIONS = (
    "suppliers",
    "request_orders",
    "supply_requests",
    "products",
    "delivery_orders",
    "supply_deliveries",
)


def _load_suppliers(base, rows):
    supplier_ids_by_ref = {}
    for ref, row in rows.items():
        payload = {key: value for key, value in row.items() if key != "ref"}
        name = payload.pop("name")
        created = get_or_create_organization(base, name, **payload)
        supplier_ids_by_ref[ref] = str(created.id)
    return supplier_ids_by_ref


def _load_products(
    base,
    facility_id,
    *,
    rows,
    product_knowledge_by_ref,
    charge_item_definitions_by_ref,
    loaded_at,
):
    product_ids_by_ref = {}
    for ref, row in rows.items():
        payload = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "ref",
                "product_knowledge_ref",
                "charge_item_definition_ref",
                "expiration_days_from_load",
            }
        }
        payload["charge_item_definition"] = charge_item_definitions_by_ref[
            row["charge_item_definition_ref"]
        ]["slug"]
        payload["expiration_date"] = (
            loaded_at + timedelta(days=row["expiration_days_from_load"])
        ).isoformat()
        created = base.create_product(
            facility_id,
            product_knowledge_by_ref[row["product_knowledge_ref"]]["slug"],
            **payload,
        )
        product_ids_by_ref[ref] = str(created.id)
    return product_ids_by_ref


def load_external_receipts(
    base,
    facility_id,
    foundation_resource_id_by_ref,
    product_knowledge_by_ref,
    charge_item_definitions_by_ref,
    *,
    loaded_at=None,
):
    pack = load_json("external_receipts")
    rows = index_rows_by_ref(pack, _COLLECTIONS)
    loaded_at = loaded_at or timezone.now()

    supplier_ids_by_ref = _load_suppliers(base, rows["suppliers"])
    request_order_ids_by_ref = load_request_orders(
        base,
        facility_id,
        rows["request_orders"],
        foundation_resource_id_by_ref,
        supplier_ids_by_ref,
    )
    supply_request_ids_by_ref = load_supply_requests(
        base,
        rows["supply_requests"],
        request_order_ids_by_ref,
        product_knowledge_by_ref,
    )
    product_ids_by_ref = _load_products(
        base,
        facility_id,
        rows=rows["products"],
        product_knowledge_by_ref=product_knowledge_by_ref,
        charge_item_definitions_by_ref=charge_item_definitions_by_ref,
        loaded_at=loaded_at,
    )
    delivery_order_ids_by_ref = load_delivery_orders(
        base,
        facility_id,
        rows["delivery_orders"],
        foundation_resource_id_by_ref,
        supplier_ids_by_ref,
    )
    load_supply_deliveries(
        base,
        rows["supply_deliveries"],
        delivery_order_rows=rows["delivery_orders"],
        delivery_order_ids_by_ref=delivery_order_ids_by_ref,
        supply_request_ids_by_ref=supply_request_ids_by_ref,
        product_ids_by_ref=product_ids_by_ref,
    )
    finalize_order_headers(
        base,
        facility_id,
        request_order_rows=rows["request_orders"],
        request_order_ids_by_ref=request_order_ids_by_ref,
        delivery_order_rows=rows["delivery_orders"],
        delivery_order_ids_by_ref=delivery_order_ids_by_ref,
    )
    return product_ids_by_ref
