from care.fixtures.loaders.inventory_helpers import (
    finalize_order_headers,
    index_rows_by_ref,
    load_delivery_orders,
    load_request_orders,
    load_supply_deliveries,
    load_supply_requests,
)
from care.fixtures.loaders.load import load_json

_PAGE_LIMIT = 200
_COLLECTIONS = (
    "request_orders",
    "supply_requests",
    "delivery_orders",
    "supply_deliveries",
)


def _load_inventory_item_ids_by_product_ref(
    base,
    facility_id,
    *,
    supply_delivery_rows,
    delivery_order_rows,
    product_ids_by_ref,
    foundation_resource_id_by_ref,
):
    selected_product_refs = {
        row["product_ref"] for row in supply_delivery_rows.values()
    }
    product_ref_by_id = {
        product_ids_by_ref[product_ref]: product_ref
        for product_ref in selected_product_refs
    }
    inventory_item_ids_by_origin_and_product = {}
    origin_refs = {
        delivery_order_rows[row["delivery_order_ref"]]["origin_ref"]
        for row in supply_delivery_rows.values()
    }

    for origin_ref in origin_refs:
        offset = 0
        while True:
            inventory_items = base.list_inventory_items(
                facility_id,
                foundation_resource_id_by_ref[origin_ref],
                limit=_PAGE_LIMIT,
                offset=offset,
            )
            for inventory_item in inventory_items:
                product_ref = product_ref_by_id.get(str(inventory_item.product.id))
                if product_ref is not None:
                    inventory_item_ids_by_origin_and_product[
                        (origin_ref, product_ref)
                    ] = str(inventory_item.id)
            if len(inventory_items) < _PAGE_LIMIT:
                break
            offset += _PAGE_LIMIT

    return inventory_item_ids_by_origin_and_product


def load_internal_transfers(
    base,
    facility_id,
    foundation_resource_id_by_ref,
    product_knowledge_by_ref,
    product_ids_by_ref,
):
    rows = index_rows_by_ref(load_json("internal_transfers"), _COLLECTIONS)

    request_order_ids_by_ref = load_request_orders(
        base,
        facility_id,
        rows["request_orders"],
        foundation_resource_id_by_ref,
    )
    supply_request_ids_by_ref = load_supply_requests(
        base,
        rows["supply_requests"],
        request_order_ids_by_ref,
        product_knowledge_by_ref,
    )
    delivery_order_ids_by_ref = load_delivery_orders(
        base,
        facility_id,
        rows["delivery_orders"],
        foundation_resource_id_by_ref,
    )
    inventory_item_ids_by_origin_and_product = _load_inventory_item_ids_by_product_ref(
        base,
        facility_id,
        supply_delivery_rows=rows["supply_deliveries"],
        delivery_order_rows=rows["delivery_orders"],
        product_ids_by_ref=product_ids_by_ref,
        foundation_resource_id_by_ref=foundation_resource_id_by_ref,
    )
    load_supply_deliveries(
        base,
        rows["supply_deliveries"],
        delivery_order_rows=rows["delivery_orders"],
        delivery_order_ids_by_ref=delivery_order_ids_by_ref,
        supply_request_ids_by_ref=supply_request_ids_by_ref,
        product_ids_by_ref=product_ids_by_ref,
        inventory_item_ids_by_origin_and_product=inventory_item_ids_by_origin_and_product,
    )
    finalize_order_headers(
        base,
        facility_id,
        request_order_rows=rows["request_orders"],
        request_order_ids_by_ref=request_order_ids_by_ref,
        delivery_order_rows=rows["delivery_orders"],
        delivery_order_ids_by_ref=delivery_order_ids_by_ref,
    )
