import secrets
from datetime import timedelta

from django.utils import timezone

from care.emr.models import (
    ChargeItemDefinition,
    InventoryItem,
    Product,
    ProductKnowledge,
)
from care.emr.models.resource_category import ResourceCategory
from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.resources.healthcare_service.spec import BaseHealthcareServiceSpec
from care.emr.resources.inventory.inventory_item.sync_inventory_item import (
    sync_inventory_item,
)

from .facilities import create_location


def _create_resource_category(facility, title, resource_type, **kwargs):
    resource_category = ResourceCategory.objects.filter(
        facility=facility, title=title, resource_type=resource_type
    ).first()
    if resource_category:
        return resource_category
    _data = {
        "facility": facility,
        "resource_type": resource_type,
        "title": title,
        "slug": f"{title.lower().replace(' ', '-')}-{resource_type}",
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
        "resource_sub_type": "other",
    }
    if kwargs:
        _data.update(kwargs)
    resource_category = ResourceCategory(**_data)
    resource_category.slug = resource_category.calculate_slug()
    resource_category.save()
    return resource_category


def _create_product_knowledge(facility, code, base_unit, **kwargs):
    coding = code.get("code", "")

    _data = {
        "facility": facility,
        "product_type": "medication",
        "status": "active",
        "storage_guidelines": [
            {
                "note": "Store in a cool, dry place away from direct sunlight.",
                "stability_duration": {
                    "unit": {
                        "code": "a",
                        "system": "http://unitsofmeasure.org",
                        "display": "year",
                    },
                    "value": 5,
                },
            }
        ],
        "code": code,
        "name": code.get("display", ""),
        "base_unit": base_unit,
        "slug": coding,
        "alternate_identifier": coding,
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
        "definitional": {},
    }
    if kwargs:
        _data.update(kwargs)
    product_knowledge = ProductKnowledge(**_data)
    product_knowledge.slug = product_knowledge.calculate_slug()
    product_knowledge.save()
    return product_knowledge


def _create_charge_item_definition(facility, title, price=None, **kwargs):
    _data = {
        "facility": facility,
        "status": "active",
        "title": title,
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
        "slug": title.lower().replace(" ", "-").replace(".", ""),
        "version": 1,
    }
    if price:
        _data["price_components"] = [
            {"amount": price, "monetary_component_type": "base"}
        ]
    if kwargs:
        _data.update(kwargs)
    charge_item_definition = ChargeItemDefinition(**_data)
    charge_item_definition.slug = charge_item_definition.calculate_slug()
    charge_item_definition.save()
    return charge_item_definition


def _create_product(facility, product_knowledge, charge_item_definition, **kwargs):
    _data = {
        "facility": facility,
        "product_knowledge": product_knowledge,
        "charge_item_definition": charge_item_definition,
        "status": "active",
        "expiration_date": timezone.now() + timedelta(days=365),
        "batch": {"lot_number": str(secrets.token_hex(5)).upper()},
        "created_by": facility.created_by,
        "updated_by": facility.created_by,
    }
    if kwargs:
        _data.update(kwargs)
    product = Product(**_data)
    product.save()
    return product


def _create_inventory_item(location, product, net_content=0):
    return InventoryItem.objects.create(
        location=location,
        product=product,
        net_content=net_content,
        status="active",
        created_by=location.created_by,
        updated_by=location.created_by,
    )


def _delivery_order(status=None, origin=None, destination=None, supplier=None, name=None):
    return DeliveryOrder.objects.create(
        status=status or "in_progress",
        origin=origin,
        destination=destination,
        supplier=supplier,
        name=name,
        created_by=origin.created_by if origin else destination.created_by,
        updated_by=origin.created_by if origin else destination.created_by,
    )


def _create_supply_delivery(
    status=None,
    supplied_item_quantity=None,
    supplied_item=None,
    supplied_inventory_item=None,
    supply_request=None,
    order=None,
):
    supply_delivery = SupplyDelivery.objects.create(
        status=status or "in_progress",
        supplied_item_quantity=supplied_item_quantity,
        supplied_item=supplied_item,
        supplied_inventory_item=supplied_inventory_item,
        supply_request=supply_request,
        delivery_type="product",
        order=order,
        created_by=order.origin.created_by
        if order.origin
        else order.destination.created_by,
        updated_by=order.origin.created_by
        if order.origin
        else order.destination.created_by,
    )
    if supply_delivery.order.origin:
        sync_inventory_item(inventory_item=supply_delivery.supplied_inventory_item)
    else:
        sync_inventory_item(
            location=supply_delivery.order.destination,
            product=supply_delivery.supplied_inventory_item.product,
        )
    return supply_delivery


def _create_object(model, facility, user=None, **kwargs):
    obj = model.de_serialize()
    obj.facility = facility
    obj.created_by = user or facility.created_by
    obj.updated_by = user or facility.updated_by
    for key, value in kwargs.items():
        setattr(obj, key, value)
    if hasattr(obj, "calculate_slug"):
        obj.slug = obj.calculate_slug()
    obj.save()
    return obj


def create_inventory_items(fake, facility, supplier, user=None):
    inventory_location = create_location(
        fake,
        user or facility.created_by,
        facility,
        [facility.default_internal_organization],
        mode="kind",
        form="ro",
        name="Pharmacy",
    )

    _create_object(
        BaseHealthcareServiceSpec(
            internal_type="pharmacy",
            name="Main Pharmacy",
            styling_metadata={},
            extra_details="",
        ),
        facility,
        user,
        locations=[inventory_location.id],
    )

    oral_tablet_definitional = {
        "dosage_form": {
            "code": "421026006",
            "system": "http://snomed.info/sct",
            "display": "Oral tablet",
        },
        "intended_routes": [
            {
                "code": "26643006",
                "system": "http://snomed.info/sct",
                "display": "Oral route",
            }
        ],
    }
    tablet_unit = {
        "system": "http://unitsofmeasure.org",
        "code": "{tbl}",
        "display": "tablets",
    }

    amoxicillin_knowledge = _create_product_knowledge(
        facility,
        {
            "code": "27658006",
            "system": "http://snomed.info/sct",
            "display": "Amoxicillin-containing product",
        },
        tablet_unit,
        definitional=oral_tablet_definitional,
        name="Amoxicillin",
        category=_create_resource_category(
            facility, "Medications", resource_type="product_knowledge"
        ),
    )
    paracetamol_knowledge = _create_product_knowledge(
        facility,
        {
            "code": "90332006",
            "system": "http://snomed.info/sct",
            "display": "Paracetamol-containing product",
        },
        tablet_unit,
        definitional=oral_tablet_definitional,
        name="Paracetamol",
        category=_create_resource_category(
            facility, "Medications", resource_type="product_knowledge"
        ),
    )
    ibuprofen_knowledge = _create_product_knowledge(
        facility,
        {
            "code": "38268001",
            "system": "http://snomed.info/sct",
            "display": "Ibuprofen-containing product",
        },
        tablet_unit,
        definitional=oral_tablet_definitional,
        name="Ibuprofen",
        category=_create_resource_category(
            facility, "Medications", resource_type="product_knowledge"
        ),
    )
    gloves = _create_product_knowledge(
        facility,
        {
            "code": "46713009",
            "system": "http://snomed.info/sct",
            "display": "Gloves",
        },
        {
            "system": "http://unitsofmeasure.org",
            "code": "{count}",
            "display": "count",
        },
        product_type="consumable",
        name="Gloves",
        category=_create_resource_category(
            facility, "Consumables", resource_type="product_knowledge"
        ),
    )

    amoxicillin_charge = _create_charge_item_definition(
        facility,
        "Amoxicillin 500mg Capsule",
        50.0,
        category=_create_resource_category(
            facility, "Medications", resource_type="charge_item_definition"
        ),
    )
    paracetamol_charge = _create_charge_item_definition(
        facility,
        "Paracetamol 500mg Tablet",
        20.0,
        category=_create_resource_category(
            facility, "Medications", resource_type="charge_item_definition"
        ),
    )
    ibuprofen_charge = _create_charge_item_definition(
        facility,
        "Ibuprofen 400mg Tablet",
        30.0,
        category=_create_resource_category(
            facility, "Medications", resource_type="charge_item_definition"
        ),
    )
    gloves_charge = _create_charge_item_definition(
        facility,
        "Pair of Gloves",
        5.0,
        category=_create_resource_category(
            facility, "Consumables", resource_type="charge_item_definition"
        ),
    )

    amoxicillin_product = _create_product(
        facility, amoxicillin_knowledge, amoxicillin_charge
    )
    paracetamol_product = _create_product(
        facility, paracetamol_knowledge, paracetamol_charge
    )
    ibuprofen_product = _create_product(
        facility, ibuprofen_knowledge, ibuprofen_charge
    )
    gloves_product = _create_product(facility, gloves, gloves_charge)

    amoxicillin_inventory_item = _create_inventory_item(
        inventory_location, amoxicillin_product
    )
    paracetamol_inventory_item = _create_inventory_item(
        inventory_location, paracetamol_product
    )
    ibuprofen_inventory_item = _create_inventory_item(
        inventory_location, ibuprofen_product
    )
    gloves_inventory_item = _create_inventory_item(
        inventory_location, gloves_product
    )

    purchase_order = _delivery_order(
        destination=inventory_location,
        supplier=supplier,
        name="Initial Stock Delivery",
        status="completed",
    )
    _create_supply_delivery(
        supplied_item=amoxicillin_product,
        supply_request=None,
        order=purchase_order,
        supplied_item_quantity=20,
        supplied_inventory_item=amoxicillin_inventory_item,
        status="completed",
    )
    _create_supply_delivery(
        supplied_item=paracetamol_product,
        supply_request=None,
        order=purchase_order,
        supplied_item_quantity=50,
        supplied_inventory_item=paracetamol_inventory_item,
        status="completed",
    )
    _create_supply_delivery(
        supplied_item=ibuprofen_product,
        supply_request=None,
        order=purchase_order,
        supplied_item_quantity=30,
        supplied_inventory_item=ibuprofen_inventory_item,
        status="completed",
    )
    _create_supply_delivery(
        supplied_item=gloves_product,
        supply_request=None,
        order=purchase_order,
        supplied_item_quantity=15,
        supplied_inventory_item=gloves_inventory_item,
        status="completed",
    )
