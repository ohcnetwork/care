from care.fixtures.loaders.load import facility_slug, load_json

_ACTIVITY_DEFINITION_META = frozenset(
    {
        "specimen_refs",
        "observation_refs",
        "charge_item_definition_refs",
        "location_refs",
        "healthcare_service_ref",
    }
)
_CHARGE_ITEM_DEFINITION_META = frozenset({"ref"})
_PRODUCT_KNOWLEDGE_META = frozenset({"ref"})


def load_specimen_definitions(base, facility_id):
    rows = load_json("specimens")
    for row in rows:
        base.create_specimen_definition(facility_id, **row)


def load_observation_definitions(base, facility_id):
    rows = load_json("observation_definitions")
    for row in rows:
        base.create_observation_definition(facility=facility_id, **row)


def load_resource_categories(base, facility_id):
    rows = load_json("resource_categories")
    for row in rows:
        base.create_resource_category(
            facility_id,
            row["title"],
            **{k: v for k, v in row.items() if k != "title"},
        )


def load_product_knowledge(base, facility_id):
    rows = load_json("product_knowledge")
    product_knowledge_by_ref: dict[str, dict[str, str]] = {}

    for row in rows:
        ref = row["ref"]
        payload = {k: v for k, v in row.items() if k not in _PRODUCT_KNOWLEDGE_META}

        category = payload.get("category")
        if category is not None:
            payload["category"] = facility_slug(facility_id, category)

        created = base.create_product_knowledge(
            facility=facility_id,
            **payload,
        )
        product_knowledge_by_ref[ref] = {
            "id": str(created.id),
            "slug": str(created.slug),
        }

    return product_knowledge_by_ref


def load_charge_item_definitions(base, facility_id):
    rows = load_json("charge_item_definitions")
    charge_item_definitions_by_ref: dict[str, dict[str, str]] = {}
    for row in rows:
        ref = row["ref"]
        payload = {
            key: value
            for key, value in row.items()
            if key not in _CHARGE_ITEM_DEFINITION_META
        }
        category = payload.get("category")
        if category is not None:
            payload["category"] = facility_slug(facility_id, category)
        created = base.create_charge_item_definition(facility_id, **payload)
        charge_item_definitions_by_ref[ref] = {
            "id": str(created.id),
            "slug": str(created.slug),
        }
    return charge_item_definitions_by_ref


def load_activity_definitions(base, facility_id, foundation_resource_id_by_ref):
    rows = load_json("activity_definitions")
    for row in rows:
        payload = {
            key: value
            for key, value in row.items()
            if key not in _ACTIVITY_DEFINITION_META
        }

        payload["specimen_requirements"] = [
            facility_slug(facility_id, slug)
            for slug in (row.get("specimen_refs") or [])
        ]
        payload["observation_result_requirements"] = [
            facility_slug(facility_id, slug)
            for slug in (row.get("observation_refs") or [])
        ]
        payload["charge_item_definitions"] = [
            facility_slug(facility_id, slug)
            for slug in (row.get("charge_item_definition_refs") or [])
        ]
        payload["locations"] = [
            foundation_resource_id_by_ref[loc_ref]
            for loc_ref in (row.get("location_refs") or [])
        ]

        healthcare_service_ref = row.get("healthcare_service_ref")
        if healthcare_service_ref is not None:
            payload["healthcare_service"] = foundation_resource_id_by_ref[
                healthcare_service_ref
            ]

        category = payload.get("category")
        if category is not None:
            payload["category"] = facility_slug(facility_id, category)

        base.create_activity_definition(facility_id, **payload)
