from rest_framework.exceptions import ValidationError

from care.emr.resources.common.monetary_component import (
    MonetaryComponents,
    MonetaryComponentType,
)
from care.utils.rounding.covert_type import convert_to_decimal
from care.utils.rounding.rounding import care_round


def calculate_amount(component, quantity, base):
    if component.amount:
        component.amount = convert_to_decimal(component.amount)
        component.amount = care_round(component.amount * quantity)
        return component
    if component.factor:
        component.factor = convert_to_decimal(component.factor)
        component.amount = care_round(base * component.factor / 100)
        return component
    raise ValidationError("Amount or factor is required")


def apply_discount_configuration(discount_components, discount_configuration):
    if discount_configuration:
        max_applicable = discount_configuration.get("max_applicable", 0)
        applicability_order = discount_configuration.get(
            "applicability_order", "total_asc"
        )
        if applicability_order == "total_asc":
            discount_components.sort(key=lambda x: convert_to_decimal(x["amount"]))
        elif applicability_order == "total_desc":
            discount_components.sort(
                key=lambda x: convert_to_decimal(x["amount"]), reverse=True
            )
        if max_applicable == 0:
            return []
        discount_components = discount_components[:max_applicable]
    return discount_components


def sync_charge_item_costs(charge_item, reverse=None):
    """
    Calculate total cost of charge item based on quantity and other factors
    """
    charge_item_price_components = MonetaryComponents(charge_item.unit_price_components)
    quantity = convert_to_decimal(charge_item.quantity)
    components = []
    total_price = 0
    base = 0
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.base.value:
            component.amount = care_round(
                convert_to_decimal(component.amount) * quantity
            )
            total_price = component.amount
            base = component.amount
            components.append(component.model_dump(mode="json", exclude_defaults=True))
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.surcharge.value:
            _component = calculate_amount(component, quantity, base)
            total_price += _component.amount
            components.append(_component.model_dump(mode="json", exclude_defaults=True))
    net_price = total_price
    discounts = []
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.discount.value:
            _component = calculate_amount(component, quantity, net_price)
            # total_price -= _component.amount
            discounts.append(_component.model_dump(mode="json", exclude_defaults=True))
    discount_configuration = charge_item.discount_configuration
    discounts = apply_discount_configuration(discounts, discount_configuration)
    for discount in discounts:
        total_price -= convert_to_decimal(discount["amount"])
        components.append(discount)
    taxable_price = total_price
    for component in charge_item_price_components:
        if component.monetary_component_type == MonetaryComponentType.tax.value:
            _component = calculate_amount(component, quantity, taxable_price)
            total_price += _component.amount
            components.append(_component.model_dump(mode="json", exclude_defaults=True))
    charge_item.total_price = total_price
    charge_item.total_price_components = components
    if charge_item.total_price < 0 and not reverse:
        raise ValidationError("Total price is less than 0")
