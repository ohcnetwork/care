import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder

from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.resources.charge_item.spec import ChargeItemReadSpec
from care.emr.resources.common.monetary_component import (
    MonetaryComponent,
    MonetaryComponentType,
)


def update_amount(price_component, total_price_components):
    if price_component["monetary_component_type"] not in total_price_components:
        total_price_components[price_component["monetary_component_type"]] = {}
    if "code" in price_component:
        key = (
            price_component["code"].get("system", "") + price_component["code"]["code"]
        )
    else:
        key = "No-Code"
    existing_component = total_price_components[
        price_component["monetary_component_type"]
    ].get(key)

    if existing_component is None:
        existing_component = MonetaryComponent(
            monetary_component_type=price_component["monetary_component_type"],
            amount=price_component["amount"],
            code=price_component.get("code"),
        ).model_dump(mode="json")
        existing_component["amount"] = Decimal(existing_component["amount"])
    else:
        existing_component["amount"] = Decimal(existing_component["amount"])
        existing_component["amount"] += Decimal(price_component["amount"])
    total_price_components[price_component["monetary_component_type"]][key] = (
        existing_component
    )


def sync_invoice_items(invoice: Invoice):
    charge_items = ChargeItem.objects.filter(id__in=invoice.charge_items)
    summary = calculate_charge_items_summary(charge_items)
    invoice.total_net = summary["net"]
    invoice.total_gross = summary["gross"]
    invoice.total_price_components = json.loads(
        json.dumps(
            summary["total_price_components"],
            cls=DjangoJSONEncoder,
        )
    )
    invoice.charge_items_copy = json.loads(
        json.dumps(
            summary["charge_items_copy"],
            cls=DjangoJSONEncoder,
        )
    )


def calculate_charge_items_summary(charge_items):
    """
    Calculate the total net, gross, price components and copy the charge items
    net amount has tax excluded
    gross amount has tax included
    """

    costs = {}
    charge_items_copy = []
    total_price_components = {}
    net = Decimal(0)
    gross = Decimal(0)

    for charge_item in charge_items:
        for price_component in charge_item.total_price_components:
            costs[price_component["monetary_component_type"]] = [
                *costs.get(price_component["monetary_component_type"], []),
                price_component,
            ]
        charge_items_copy.append(ChargeItemReadSpec.serialize(charge_item).to_json())

    for price_component in costs.get(MonetaryComponentType.base.value, []):
        update_amount(price_component, total_price_components)
        net += Decimal(price_component["amount"])
    total_price_components[MonetaryComponentType.surcharge.value] = {}
    for price_component in costs.get(MonetaryComponentType.surcharge.value, []):
        update_amount(price_component, total_price_components)
        net += Decimal(price_component["amount"])
    for price_component in costs.get(MonetaryComponentType.discount.value, []):
        update_amount(price_component, total_price_components)
        net -= Decimal(price_component["amount"])
    gross = net
    for price_component in costs.get(MonetaryComponentType.tax.value, []):
        update_amount(price_component, total_price_components)
        gross += Decimal(price_component["amount"])

    final_price_components = []
    for price_component in total_price_components.values():
        final_price_components.extend(list(price_component.values()))

    return {
        "net": net,
        "gross": gross,
        "total_price_components": final_price_components,
        "charge_items_copy": charge_items_copy,
    }
