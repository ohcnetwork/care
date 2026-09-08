_ORDER_META = frozenset(
    {
        "ref",
        "supplier_ref",
        "origin_ref",
        "destination_ref",
        "final_status",
    }
)


def index_rows_by_ref(pack, collections):
    return {
        collection: {row["ref"]: row for row in pack[collection]}
        for collection in collections
    }


def _resolve_order_relationships(
    row,
    foundation_resource_id_by_ref,
    supplier_ids_by_ref,
):
    relationships = {}
    supplier_ref = row.get("supplier_ref")
    if supplier_ref:
        relationships["supplier"] = supplier_ids_by_ref[supplier_ref]
    origin_ref = row.get("origin_ref")
    if origin_ref:
        relationships["origin"] = foundation_resource_id_by_ref[origin_ref]
    return relationships


def load_request_orders(
    base,
    facility_id,
    rows,
    foundation_resource_id_by_ref,
    supplier_ids_by_ref=None,
):
    supplier_ids_by_ref = supplier_ids_by_ref or {}
    request_order_ids_by_ref = {}
    for ref, row in rows.items():
        relationships = _resolve_order_relationships(
            row,
            foundation_resource_id_by_ref,
            supplier_ids_by_ref,
        )
        destination_id = foundation_resource_id_by_ref[row["destination_ref"]]
        request_order_ids_by_ref[ref] = str(
            _create_request_order_from_row(
                base,
                facility_id,
                row,
                destination_id,
                **relationships,
            ).id
        )
    return request_order_ids_by_ref


def _create_request_order_from_row(
    base, facility_id, row, destination_id, **relationships
):
    payload = {key: value for key, value in row.items() if key not in _ORDER_META}
    name = payload.pop("name")
    return base.create_request_order(
        facility_id,
        name,
        destination_id,
        **relationships,
        **payload,
    )


def load_delivery_orders(
    base,
    facility_id,
    rows,
    foundation_resource_id_by_ref,
    supplier_ids_by_ref=None,
):
    supplier_ids_by_ref = supplier_ids_by_ref or {}
    delivery_order_ids_by_ref = {}
    for ref, row in rows.items():
        relationships = _resolve_order_relationships(
            row,
            foundation_resource_id_by_ref,
            supplier_ids_by_ref,
        )
        destination_id = foundation_resource_id_by_ref[row["destination_ref"]]
        delivery_order_ids_by_ref[ref] = str(
            _create_delivery_order_from_row(
                base,
                facility_id,
                row,
                destination_id,
                **relationships,
            ).id
        )
    return delivery_order_ids_by_ref


def _create_delivery_order_from_row(
    base, facility_id, row, destination_id, **relationships
):
    payload = {key: value for key, value in row.items() if key not in _ORDER_META}
    name = payload.pop("name")
    return base.create_delivery_order(
        facility_id,
        name,
        destination_id,
        **relationships,
        **payload,
    )


def load_supply_requests(
    base,
    rows,
    request_order_ids_by_ref,
    product_knowledge_by_ref,
):
    supply_request_ids_by_ref = {}
    for ref, row in rows.items():
        created = base.create_supply_request(
            request_order_ids_by_ref[row["request_order_ref"]],
            product_knowledge_by_ref[row["product_knowledge_ref"]]["id"],
            row["quantity"],
            status=row["status"],
        )
        supply_request_ids_by_ref[ref] = str(created.id)
    return supply_request_ids_by_ref


def load_supply_deliveries(
    base,
    rows,
    *,
    delivery_order_rows,
    delivery_order_ids_by_ref,
    supply_request_ids_by_ref,
    product_ids_by_ref,
    inventory_item_ids_by_origin_and_product=None,
):
    inventory_item_ids_by_origin_and_product = (
        inventory_item_ids_by_origin_and_product or {}
    )
    for row in rows.values():
        delivery_order_ref = row["delivery_order_ref"]
        delivery_order_row = delivery_order_rows[delivery_order_ref]
        origin_ref = delivery_order_row.get("origin_ref")
        item = {}
        if origin_ref:
            item["supplied_inventory_item"] = inventory_item_ids_by_origin_and_product[
                (origin_ref, row["product_ref"])
            ]
        else:
            item["supplied_item"] = product_ids_by_ref[row["product_ref"]]

        created = base.create_supply_delivery(
            delivery_order_ids_by_ref[delivery_order_ref],
            row["supplied_item_quantity"],
            status="in_progress",
            supply_request=supply_request_ids_by_ref[row["supply_request_ref"]],
            supplied_item_condition=row["supplied_item_condition"],
            supplied_item_pack_quantity=row["supplied_item_pack_quantity"],
            supplied_item_pack_size=row["supplied_item_pack_size"],
            total_purchase_price=row.get("total_purchase_price"),
            extensions=row["extensions"],
            **item,
        )
        if row["status"] != "in_progress":
            base.update_supply_delivery(str(created.id), status=row["status"])


def finalize_request_order(base, facility_id, row, order_id):
    if row["final_status"] == row["status"]:
        return
    base.update_request_order(
        facility_id,
        order_id,
        status=row["final_status"],
        name=row["name"],
        note=row.get("note"),
        intent=row["intent"],
        category=row["category"],
        priority=row["priority"],
        reason=row["reason"],
    )


def finalize_delivery_order(base, facility_id, row, order_id):
    if row["final_status"] == row["status"]:
        return
    base.update_delivery_order(
        facility_id,
        order_id,
        status=row["final_status"],
        name=row["name"],
        note=row.get("note"),
    )


def finalize_order_headers(
    base,
    facility_id,
    *,
    request_order_rows,
    request_order_ids_by_ref,
    delivery_order_rows,
    delivery_order_ids_by_ref,
):
    for ref, row in request_order_rows.items():
        finalize_request_order(base, facility_id, row, request_order_ids_by_ref[ref])
    for ref, row in delivery_order_rows.items():
        finalize_delivery_order(base, facility_id, row, delivery_order_ids_by_ref[ref])
